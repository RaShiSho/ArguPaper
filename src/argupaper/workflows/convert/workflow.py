"""Workflow for PDF to Markdown conversion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from argupaper.config import Config
from argupaper.services.pdf import ConversionResult, MarkdownCache, MinerUClient, PDFPipeline
from argupaper.workflows.convert.options import ConvertOptions
from argupaper.workflows.convert.result import ConvertWorkflowResult, FolderConvertSummary
from argupaper.workflows.errors import InputValidationError

ProgressCallback = Optional[Callable[[str], None]]
FileEventCallback = Optional[Callable[[str], None]]
CONVERT_RUN_LOG_DIRNAME = "convert_runs"


class ConvertWorkflow:
    """Convert local PDFs to cached Markdown."""

    def __init__(self, config: Config):
        self.config = config

    async def run(
        self,
        options: ConvertOptions,
        progress_callback: ProgressCallback = None,
        file_event_callback: FileEventCallback = None,
    ) -> ConvertWorkflowResult:
        """Run a single-file or folder conversion."""

        self._validate_options(options)
        cache, pipeline = self._build_pipeline()
        if options.folder_path is not None:
            return await self._run_folder(options, cache, pipeline, progress_callback, file_event_callback)
        return await self._run_single(options, cache, pipeline, progress_callback)

    def _build_pipeline(self) -> tuple[MarkdownCache, PDFPipeline]:
        cache = MarkdownCache(cache_dir=self.config.pdf.cache_dir)
        mineru_client = MinerUClient(
            api_key=self.config.pdf.api_key,
            model_version="vlm",
            api_endpoint=self.config.pdf.api_endpoint,
        )
        pipeline = PDFPipeline(
            mineru_client=mineru_client,
            cache=cache,
            public_url_base=self.config.pdf.public_url_base,
        )
        return cache, pipeline

    async def _run_single(
        self,
        options: ConvertOptions,
        cache: MarkdownCache,
        pipeline: PDFPipeline,
        progress_callback: ProgressCallback,
    ) -> ConvertWorkflowResult:
        if options.pdf_path is None:
            raise InputValidationError("Convert requires a local PDF path or --folder <dir>.")
        try:
            if progress_callback:
                progress_callback("Converting PDF to Markdown...")
            result = await pipeline.process(options.pdf_path, force_reconvert=options.force_reconvert)
        finally:
            await pipeline.close()

        markdown = result.markdown or ""
        if options.output_path is not None:
            options.output_path.parent.mkdir(parents=True, exist_ok=True)
            options.output_path.write_text(markdown, encoding="utf-8")

        return ConvertWorkflowResult(
            conversion=result,
            input_path=options.pdf_path,
            cache_path=cache.get_markdown_path(result.cache_key).absolute(),
            output_path=options.output_path,
        )

    async def _run_folder(
        self,
        options: ConvertOptions,
        cache: MarkdownCache,
        pipeline: PDFPipeline,
        progress_callback: ProgressCallback,
        file_event_callback: FileEventCallback,
    ) -> ConvertWorkflowResult:
        folder_path = options.folder_path
        if folder_path is None:
            raise InputValidationError("Convert requires a local PDF path or --folder <dir>.")

        try:
            entries = sorted(folder_path.iterdir(), key=lambda entry: entry.name.casefold())
        except OSError as exc:
            raise InputValidationError(f"Cannot read folder: {folder_path}, error: {exc}") from exc

        run_id, log_path = self._new_run_log_path()
        summary = FolderConvertSummary(total_entries=len(entries))
        self._write_run_event(
            log_path,
            run_id=run_id,
            event="run_start",
            status="running",
            input_path=folder_path,
            force_reconvert=options.force_reconvert,
            total_entries=len(entries),
        )

        try:
            for index, entry in enumerate(entries, start=1):
                if progress_callback:
                    progress_callback(f"Processing {index}/{len(entries)}: {entry.name}")
                skip_reason = self._get_skip_reason(entry)
                if skip_reason is not None:
                    summary.skipped += 1
                    self._write_run_event(
                        log_path,
                        run_id=run_id,
                        event="file_skipped",
                        status="skipped",
                        input_path=entry,
                        reason=skip_reason,
                    )
                    if file_event_callback:
                        file_event_callback(f"Skipped {entry.name}: {skip_reason}")
                    continue

                summary.processed += 1
                try:
                    result = await pipeline.process(entry, force_reconvert=options.force_reconvert)
                    summary.success += 1
                    if result.from_cache:
                        summary.cache_hits += 1
                    cache_path = cache.get_markdown_path(result.cache_key).absolute()
                    self._write_run_event(
                        log_path,
                        run_id=run_id,
                        event="file_success",
                        status="success",
                        input_path=entry,
                        cache_key=result.cache_key,
                        cache_path=str(cache_path),
                        from_cache=result.from_cache,
                    )
                    if file_event_callback:
                        source = "cache" if result.from_cache else "new"
                        file_event_callback(f"Converted {entry.name} ({source}): {result.cache_key}")
                except Exception as exc:  # noqa: BLE001 - batch conversion records per-file failures
                    summary.failed += 1
                    self._write_run_event(
                        log_path,
                        run_id=run_id,
                        event="file_failed",
                        status="failed",
                        input_path=entry,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    if file_event_callback:
                        file_event_callback(f"Failed {entry.name}: {exc}")
        finally:
            await pipeline.close()

        self._write_run_event(
            log_path,
            run_id=run_id,
            event="run_summary",
            status="completed",
            input_path=folder_path,
            **summary.model_dump(),
        )
        return ConvertWorkflowResult(summary=summary, input_path=folder_path, run_log_path=log_path)

    def _validate_options(self, options: ConvertOptions) -> None:
        if options.pdf_path is not None and options.folder_path is not None:
            raise InputValidationError("Use either a PDF path or --folder, not both.")
        if options.pdf_path is None and options.folder_path is None:
            raise InputValidationError("Convert requires a local PDF path or --folder <dir>.")
        if options.folder_path is not None and options.output_path is not None:
            raise InputValidationError("--output is only supported for single-file conversion.")

        if options.pdf_path is not None:
            if not options.pdf_path.exists():
                raise InputValidationError(f"PDF file not found: {options.pdf_path}")
            if options.pdf_path.suffix.lower() != ".pdf":
                raise InputValidationError("Input must be a .pdf file.")
        if options.folder_path is not None:
            if not options.folder_path.exists():
                raise InputValidationError(f"Folder not found: {options.folder_path}")
            if not options.folder_path.is_dir():
                raise InputValidationError(f"--folder must point to a directory: {options.folder_path}")

    def _new_run_log_path(self) -> tuple[str, Path]:
        run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        log_path = Path(self.config.data_path) / CONVERT_RUN_LOG_DIRNAME / f"{run_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return run_id, log_path

    def _write_run_event(
        self,
        log_path: Path,
        *,
        run_id: str,
        event: str,
        status: str,
        input_path: Path | None = None,
        **details: object,
    ) -> None:
        payload: dict[str, object] = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "status": status,
        }
        if input_path is not None:
            payload["input_path"] = str(input_path.absolute())
        payload.update(details)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _get_skip_reason(self, entry: Path) -> str | None:
        try:
            if entry.is_dir():
                return "directory"
            if not entry.is_file():
                return "not a regular file"
        except OSError as exc:
            return f"unreadable entry: {exc}"
        if entry.suffix.lower() != ".pdf":
            return "not a PDF file"
        return None


__all__ = ["ConvertWorkflow"]
