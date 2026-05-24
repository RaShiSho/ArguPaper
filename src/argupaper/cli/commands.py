"""CLI commands for ArguPaper."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer
from click import IntRange
from click.core import ParameterSource
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from argupaper.cli.formatters import (
    format_analyze_summary,
    format_error,
    format_info,
    format_paper_detail,
    format_paper_records,
    format_search_results,
    format_success,
    format_warnings,
    render_markdown,
)
from argupaper.agents.search import SearchClarificationResponse
from argupaper.config import Config, load_config
from argupaper.memory.paper_store import PaperStore
from argupaper.pdf import ConversionResult, MarkdownCache, MinerUClient, PDFPipeline
from argupaper.workflows import (
    AnalyzeOptions,
    AnalyzeWorkflow,
    ExternalServiceError,
    InputValidationError,
    SearchOptions,
)
from argupaper.workflows.models import SearchClarification
from argupaper.workflows.search_agent import SearchAgentWorkflow


console = Console()
SPINNER_NAME = "line"
DEFAULT_OUTPUT_DIR = Path("output")
CONVERT_RUN_LOG_DIRNAME = "convert_runs"


def build_analyze_workflow() -> AnalyzeWorkflow:
    """Construct the default analyze workflow."""

    config = load_config(require_pdf_api_key=False)
    return AnalyzeWorkflow(config)


def build_search_agent_workflow() -> SearchAgentWorkflow:
    """Construct the default search-agent workflow."""

    config = load_config(require_pdf_api_key=False)
    return SearchAgentWorkflow(config)


def build_search_workflow() -> SearchAgentWorkflow:
    """Backward-compatible alias for the search-agent workflow builder."""

    return build_search_agent_workflow()


def resolve_analyze_output_path(output: str | None) -> Path | None:
    """Resolve analyze output paths.

    A bare filename such as "1.md" is saved under output/ by default. Explicit
    paths like "reports/1.md", ".\\1.md", or absolute paths keep their meaning.
    """

    if output is None:
        return None

    output_path = Path(output)
    has_explicit_path = any(separator in output for separator in ("/", "\\"))
    if output_path.is_absolute() or has_explicit_path:
        return output_path
    return DEFAULT_OUTPUT_DIR / output_path


def resolve_convert_output_path(output: str | None) -> Path | None:
    """Resolve convert export output paths exactly as provided."""

    if output is None:
        return None
    return Path(output)


def resolve_auto_report_path(paper_path: Path) -> Path:
    """Build the default report path from the input paper filename."""

    return DEFAULT_OUTPUT_DIR / f"{paper_path.stem}.md"


def build_convert_pipeline(config: Config) -> tuple[MarkdownCache, PDFPipeline]:
    """Construct the default PDF conversion cache and pipeline."""

    cache = MarkdownCache(cache_dir=config.pdf.cache_dir)
    mineru_client = MinerUClient(
        api_key=config.pdf.api_key,
        model_version="vlm",
        api_endpoint=config.pdf.api_endpoint,
    )
    pipeline = PDFPipeline(
        mineru_client=mineru_client,
        cache=cache,
        public_url_base=config.pdf.public_url_base,
    )
    return cache, pipeline


def build_paper_store() -> PaperStore:
    """Construct the default local paper store."""

    config = load_config(require_pdf_api_key=False)
    return PaperStore(storage_path=config.paper_storage_path)


async def _convert_pdf_with_pipeline(
    pipeline: PDFPipeline,
    pdf_path: Path,
    force_reconvert: bool,
) -> ConversionResult:
    """Run PDF conversion and close pipeline resources in the same event loop."""

    try:
        return await pipeline.process(pdf_path, force_reconvert=force_reconvert)
    finally:
        await pipeline.close()


def _validate_convert_inputs(pdf: str | None, folder: str | None, output: str | None) -> tuple[Path | None, Path | None]:
    """Validate convert input mode and return resolved paths."""

    if pdf and folder:
        raise InputValidationError("Use either a PDF path or --folder, not both.")
    if not pdf and not folder:
        raise InputValidationError("Convert requires a local PDF path or --folder <dir>.")
    if folder and output:
        raise InputValidationError("--output is only supported for single-file conversion.")

    if pdf:
        if pdf.startswith(("http://", "https://")):
            raise InputValidationError("URL conversion is not supported. Please use a local PDF path.")
        pdf_path = Path(pdf)
        if not pdf_path.exists():
            raise InputValidationError(f"PDF file not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise InputValidationError("Input must be a .pdf file.")
        return pdf_path, None

    folder_path = Path(str(folder))
    if not folder_path.exists():
        raise InputValidationError(f"Folder not found: {folder_path}")
    if not folder_path.is_dir():
        raise InputValidationError(f"--folder must point to a directory: {folder_path}")
    return None, folder_path


def _new_convert_run_log_path(data_path: str) -> tuple[str, Path]:
    """Create a traceable run id and log path for a folder conversion run."""

    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    log_path = Path(data_path) / CONVERT_RUN_LOG_DIRNAME / f"{run_id}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return run_id, log_path


def _write_convert_run_event(
    log_path: Path,
    *,
    run_id: str,
    event: str,
    status: str,
    input_path: Path | None = None,
    **details: object,
) -> None:
    """Append one JSONL event to a folder conversion run log."""

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


async def _convert_folder_with_pipeline(
    pipeline: PDFPipeline,
    cache: MarkdownCache,
    folder_path: Path,
    force_reconvert: bool,
    run_id: str,
    log_path: Path,
) -> dict[str, int]:
    """Convert all direct PDF files in a folder and write a JSONL run log."""

    try:
        entries = sorted(folder_path.iterdir(), key=lambda entry: entry.name.casefold())
    except OSError as exc:
        raise InputValidationError(f"Cannot read folder: {folder_path}, error: {exc}") from exc

    summary = {
        "total_entries": len(entries),
        "processed": 0,
        "success": 0,
        "cache_hits": 0,
        "failed": 0,
        "skipped": 0,
    }
    _write_convert_run_event(
        log_path,
        run_id=run_id,
        event="run_start",
        status="running",
        input_path=folder_path,
        force_reconvert=force_reconvert,
        total_entries=len(entries),
    )

    try:
        with Progress(
            SpinnerColumn(SPINNER_NAME),
            TextColumn("[progress.description]{task.description}"),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scanning folder...", total=len(entries))
            for index, entry in enumerate(entries, start=1):
                progress.update(
                    task,
                    description=f"[cyan]Processing {index}/{len(entries)}: {entry.name}",
                )

                skip_reason = _get_convert_skip_reason(entry)
                if skip_reason is not None:
                    summary["skipped"] += 1
                    _write_convert_run_event(
                        log_path,
                        run_id=run_id,
                        event="file_skipped",
                        status="skipped",
                        input_path=entry,
                        reason=skip_reason,
                    )
                    progress.console.print(format_info(f"Skipped {entry.name}: {skip_reason}"))
                    progress.advance(task)
                    continue

                summary["processed"] += 1
                try:
                    result = await pipeline.process(entry, force_reconvert=force_reconvert)
                    summary["success"] += 1
                    if result.from_cache:
                        summary["cache_hits"] += 1
                    cache_path = cache.get_markdown_path(result.cache_key).absolute()
                    _write_convert_run_event(
                        log_path,
                        run_id=run_id,
                        event="file_success",
                        status="success",
                        input_path=entry,
                        cache_key=result.cache_key,
                        cache_path=str(cache_path),
                        from_cache=result.from_cache,
                    )
                    progress.console.print(
                        format_success(
                            f"Converted {entry.name} "
                            f"({'cache' if result.from_cache else 'new'}): {result.cache_key}"
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - batch mode records per-file failures and continues
                    summary["failed"] += 1
                    _write_convert_run_event(
                        log_path,
                        run_id=run_id,
                        event="file_failed",
                        status="failed",
                        input_path=entry,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    progress.console.print(format_error(exc))
                progress.advance(task)

            progress.update(task, completed=len(entries))
    finally:
        await pipeline.close()

    _write_convert_run_event(
        log_path,
        run_id=run_id,
        event="run_summary",
        status="completed",
        input_path=folder_path,
        **summary,
    )
    return summary


def _get_convert_skip_reason(entry: Path) -> str | None:
    """Return a skip reason for a folder entry, or None when it is an eligible PDF."""

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


def convert(
    pdf: Optional[str] = typer.Argument(None, help="Path to local PDF file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Optional Markdown export path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reconvert even if cached"),
    folder: Optional[str] = typer.Option(
        None,
        "--folder",
        "-d",
        help="Convert all direct PDF files in a folder",
    ),
) -> None:
    """Convert a local PDF to Markdown and store it in the cache."""

    try:
        pdf_path, folder_path = _validate_convert_inputs(pdf, folder, output)
        config = load_config(require_pdf_api_key=True)
        cache, pipeline = build_convert_pipeline(config)

        if folder_path is not None:
            run_id, log_path = _new_convert_run_log_path(config.data_path)
            summary = asyncio.run(
                _convert_folder_with_pipeline(
                    pipeline=pipeline,
                    cache=cache,
                    folder_path=folder_path,
                    force_reconvert=force,
                    run_id=run_id,
                    log_path=log_path,
                )
            )
            console.print(format_success("Folder conversion complete"))
            console.print(format_info(f"Folder: {folder_path.absolute()}"))
            console.print(format_info(f"Total entries: {summary['total_entries']}"))
            console.print(format_info(f"Processed PDFs: {summary['processed']}"))
            console.print(format_info(f"Succeeded: {summary['success']}"))
            console.print(format_info(f"Loaded from cache: {summary['cache_hits']}"))
            console.print(format_info(f"Failed: {summary['failed']}"))
            console.print(format_info(f"Skipped: {summary['skipped']}"))
            console.print(f"[dim]Run log: {log_path.absolute()}[/dim]")
            return

        with Progress(
            SpinnerColumn(SPINNER_NAME),
            TextColumn("[progress.description]{task.description}"),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Converting PDF to Markdown...", total=None)
            if pdf_path is None:
                raise InputValidationError("Convert requires a local PDF path or --folder <dir>.")
            result = asyncio.run(_convert_pdf_with_pipeline(pipeline, pdf_path, force))
            progress.update(task, completed=True)

        markdown = result.markdown or ""
        output_path = resolve_convert_output_path(output)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding="utf-8")

        console.print(format_success("Conversion complete"))
        console.print(format_info(f"Original filename: {pdf_path.name}"))
        console.print(format_info(f"Cache key: {result.cache_key}"))
        console.print(format_info(f"Cache path: {cache.get_markdown_path(result.cache_key).absolute()}"))
        console.print(format_info(f"Loaded from cache: {'yes' if result.from_cache else 'no'}"))
        if output_path is not None:
            console.print(f"[dim]Markdown exported to: {output_path.absolute()}[/dim]")
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def analyze(
    paper: str = typer.Argument(..., help="Converted paper name, cache key, or legacy local PDF path"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    save_report: bool = typer.Option(
        False,
        "--save-report",
        help="Save report markdown to output/<paper-filename>.md when --output is not set",
    ),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of debate rounds"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reconvert even if cached"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Analyze a research paper with multi-agent debate."""

    try:
        if paper.startswith(("http://", "https://")):
            raise InputValidationError(
                "URL analysis is not part of the MVP CLI. Please use a converted paper name or local PDF path."
            )
        if rounds <= 0:
            raise InputValidationError("--rounds must be greater than 0.")

        paper_path = Path(paper)
        analyze_options: dict[str, object]
        if paper_path.exists():
            if paper_path.suffix.lower() != ".pdf":
                raise InputValidationError("Input must be a converted paper name or a .pdf file.")
            analyze_options = {"paper_path": paper_path}
        else:
            analyze_options = {"paper_name": paper}

        workflow = build_analyze_workflow()
        output_path = resolve_analyze_output_path(output)
        if output_path is None and save_report:
            output_path = resolve_auto_report_path(Path(paper))

        _run_analyze(
            workflow=workflow,
            options=AnalyzeOptions(
                **analyze_options,
                output_path=output_path,
                rounds=rounds,
                force_reconvert=force,
                verbose=verbose,
            ),
        )
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _run_analyze(workflow: AnalyzeWorkflow, options: AnalyzeOptions) -> None:
    """Run the analysis workflow synchronously."""

    with Progress(
        SpinnerColumn(SPINNER_NAME),
        TextColumn("[progress.description]{task.description}"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Preparing analysis...", total=None)

        def progress_callback(message: str) -> None:
            progress.update(task, description=f"[cyan]{message}")

        result = workflow.run_sync(options, progress_callback)
        progress.update(task, completed=True)

    console.print(format_success("Analysis complete"))
    if result.from_cache:
        console.print("[dim]Result loaded from cache (use --force to reconvert)[/dim]\n")

    format_analyze_summary(result)
    if result.warnings:
        format_warnings(result.warnings)

    if options.verbose:
        console.print(format_info(f"Report title: {result.report_title}"))

    if options.output_path:
        options.output_path.parent.mkdir(parents=True, exist_ok=True)
        options.output_path.write_text(result.report_markdown, encoding="utf-8")
        console.print(f"[dim]Report saved to: {options.output_path.absolute()}[/dim]")

    console.print(render_markdown(result.report_markdown))


def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results"),
    source: str = typer.Option(
        "both",
        "--source",
        "-s",
        help="Search source: semantic_scholar, arxiv, google_scholar, serpapi, or both",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Search for academic papers."""

    try:
        if limit <= 0:
            raise InputValidationError("--limit must be greater than 0.")
        if source not in {"semantic_scholar", "arxiv", "google_scholar", "serpapi", "both"}:
            raise InputValidationError(
                "--source must be one of: semantic_scholar, arxiv, google_scholar, serpapi, both."
            )

        workflow = build_search_agent_workflow()
        limit_overridden = ctx.get_parameter_source("limit") == ParameterSource.COMMANDLINE
        source_overridden = ctx.get_parameter_source("source") == ParameterSource.COMMANDLINE
        _run_search(
            workflow=workflow,
            options=SearchOptions(
                query=query,
                limit=limit,
                source=source,
                verbose=verbose,
                raw_request=query,
                requested_limit=limit if limit_overridden else None,
                interactive=sys.stdin.isatty() and sys.stdout.isatty(),
                limit_overridden=limit_overridden,
                source_overridden=source_overridden,
            ),
        )
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _run_search(workflow: SearchAgentWorkflow, options: SearchOptions) -> None:
    """Run paper search."""

    with Progress(
        SpinnerColumn(SPINNER_NAME),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Searching: {options.query}...", total=None)

        def progress_callback(message: str) -> None:
            progress.update(task, description=f"[cyan]{message}")

        result = workflow.run_sync(
            options,
            progress_callback,
            clarification_callback=_resolve_search_clarification if options.interactive else None,
        )
        progress.update(task, completed=True)

    if result.warnings:
        format_warnings(result.warnings)

    if (
        not result.results
        and result.retrieved_count == 0
        and any("search failed" in warning.lower() for warning in result.warnings)
    ):
        raise ExternalServiceError("All search sources failed.")

    console.print(format_success("Search complete"))
    if not result.results:
        format_warnings(["Search completed but returned no results. Try a broader query or another source."])
    if options.verbose:
        console.print(format_info(f"Parser: {result.parse_result.parser}"))
        console.print(
            format_info(f"Parsed keywords: {', '.join(result.parse_result.filters.keywords) or 'N/A'}")
        )
        console.print(format_info(f"Expanded queries: {', '.join(result.expanded_queries)}"))
        console.print(format_info(f"Source stats: {result.source_stats}"))
        console.print(
            format_info(
                "Filter summary: "
                f"retrieved={result.retrieved_count}, filtered={result.filtered_count}, "
                f"candidate_limit={result.candidate_limit}"
            )
        )

    format_search_results(result)
    console.print(f"[dim]Trace saved to: {Path(result.trace_dir).absolute()}[/dim]")


def papers(
    paper_id: Optional[str] = typer.Argument(
        None,
        help="Saved paper ID or unique hash prefix. Omit to list saved records.",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Search saved records by title, source, paper ID, or structured summary.",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum records to display"),
    report: bool = typer.Option(False, "--report", help="Render the saved report for a paper"),
    markdown: bool = typer.Option(False, "--markdown", help="Render the saved paper markdown"),
) -> None:
    """Inspect locally saved paper analysis records."""

    try:
        if paper_id and query:
            raise InputValidationError("Use either a paper_id argument or --query, not both.")
        if limit <= 0:
            raise InputValidationError("--limit must be greater than 0.")

        store = build_paper_store()
        if paper_id:
            record = asyncio.run(store.get_paper(paper_id))
            if record is None:
                raise InputValidationError(f"Saved paper record not found: {paper_id}")
            format_paper_detail(record)
            if report:
                saved_report = str(record.get("report", "")).strip()
                if saved_report:
                    console.print(render_markdown(saved_report))
                else:
                    console.print("[dim]No saved report found for this paper.[/dim]")
            if markdown:
                saved_markdown = str(record.get("markdown", "")).strip()
                if saved_markdown:
                    console.print(render_markdown(saved_markdown))
                else:
                    console.print("[dim]No saved markdown found for this paper.[/dim]")
            return

        records = (
            asyncio.run(store.search_papers(query))
            if query
            else asyncio.run(store.list_papers())
        )
        format_paper_records(records[:limit])
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _resolve_search_clarification(item: SearchClarification) -> SearchClarificationResponse:
    """Interactively resolve one ambiguous search filter."""

    console.print(format_info(item.prompt))
    for index, option in enumerate(item.options, start=1):
        console.print(f"[dim]{index}. {option.label}[/dim]")

    choice = typer.prompt(
        "Select an option",
        type=IntRange(1, len(item.options)),
    )
    selected = item.options[choice - 1]
    return SearchClarificationResponse(
        field=item.field,
        selected_value=selected.value,
        selected_label=selected.label,
    )


def get_app() -> typer.Typer:
    """Get the Typer app instance for programmatic use."""

    from argupaper.cli import app

    return app
