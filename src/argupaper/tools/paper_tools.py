"""PaperStore-backed tool wrappers for Agents."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from argupaper.config import Config
from argupaper.memory.paper_store import PaperStore
from argupaper.tools.registry import ToolRegistry
from argupaper.tools.schemas import ListPapersArgs, ReadPaperContextArgs, SelectPaperArgs, ToolResult
from argupaper.workflows.papers import PapersOptions, PapersWorkflow

ProgressCallback = Callable[[str], None] | None


def register_paper_tools(
    registry: ToolRegistry,
    config: Config,
    *,
    progress_callback: ProgressCallback = None,
) -> None:
    """Register PaperStore-backed tools."""

    toolbox = PaperToolbox(config, progress_callback=progress_callback)
    registry.register(
        "list_papers",
        "List or search papers saved in the local PaperStore.",
        toolbox.list_papers,
        args_schema=ListPapersArgs,
    )
    registry.register(
        "select_paper",
        "Select a paper by id, unique prefix, title, source, or query.",
        toolbox.select_paper,
        args_schema=SelectPaperArgs,
    )
    registry.register(
        "read_paper_context",
        "Read metadata, structured summary, markdown excerpt, and report excerpt for a paper.",
        toolbox.read_paper_context,
        args_schema=ReadPaperContextArgs,
    )


class PaperToolbox:
    """PaperStore operations exposed as reusable Agent tools."""

    def __init__(self, config: Config, *, progress_callback: ProgressCallback = None) -> None:
        self.paper_store = PaperStore(storage_path=config.paper_storage_path)
        self.progress_callback = progress_callback

    async def list_papers(self, query: str | None = None, limit: int = 20) -> ToolResult:
        """List saved papers through PapersWorkflow or run loose local keyword search."""

        self._progress("Listing saved papers...")
        normalized_query = query.strip() if query else None
        if normalized_query:
            all_records = await self.paper_store.list_papers()
            records, tokens = await self._search_local_records(normalized_query, all_records)
            limited_records = records[:limit]
            return ToolResult(
                tool="list_papers",
                ok=True,
                summary=self._summarize_records(
                    limited_records,
                    query=normalized_query,
                    total_count=len(all_records),
                    matched_count=len(records),
                ),
                data={
                    "records": limited_records,
                    "count": len(limited_records),
                    "total_count": len(all_records),
                    "matched_count": len(records),
                    "query": normalized_query,
                    "tokens": tokens,
                },
            )

        result = await PapersWorkflow(self.paper_store).run(PapersOptions(limit=limit))
        records = result.records
        return ToolResult(
            tool="list_papers",
            ok=True,
            summary=self._summarize_records(records, total_count=len(records)),
            data={"records": records, "count": len(records), "total_count": len(records)},
        )

    async def select_paper(self, paper: str) -> ToolResult:
        """Select one paper from PaperStore."""

        self._progress(f"Selecting paper: {paper}...")
        query = paper.strip()
        record = await self.paper_store.get_paper(query)
        if record is not None:
            selected = self._selected_from_record(record)
            return ToolResult(
                tool="select_paper",
                ok=True,
                summary=f"Selected paper {selected['paper_id']}: {selected['title']}",
                data={"selected_paper": selected, "record": self._record_metadata(record)},
            )

        records = await self.paper_store.search_papers(query)
        exact = [
            item
            for item in records
            if query.lower()
            in {
                str(item.get("paper_id", "")).lower(),
                str(item.get("title", "")).lower(),
                str(item.get("source", "")).lower(),
            }
        ]
        candidates = exact or records
        if len(candidates) == 1:
            record = await self.paper_store.get_paper(str(candidates[0].get("paper_id", "")))
            if record is not None:
                selected = self._selected_from_record(record)
                return ToolResult(
                    tool="select_paper",
                    ok=True,
                    summary=f"Selected paper {selected['paper_id']}: {selected['title']}",
                    data={"selected_paper": selected, "record": self._record_metadata(record)},
                )

        if candidates:
            return ToolResult(
                tool="select_paper",
                ok=False,
                summary="Multiple papers matched. Use a more specific paper id or title.",
                data={"candidates": candidates[:8]},
            )
        return ToolResult(
            tool="select_paper",
            ok=False,
            summary=f"No saved paper matched: {paper}",
            data={},
        )

    async def read_paper_context(self, paper_id: str | None = None, max_chars: int = 6000) -> ToolResult:
        """Read paper context from PaperStore."""

        if not paper_id:
            return ToolResult(
                tool="read_paper_context",
                ok=False,
                summary="No paper is selected. Use /use <paper-id-or-name> first.",
                data={},
            )
        self._progress(f"Reading paper context for {paper_id}...")
        record = await self.paper_store.get_paper(paper_id)
        if record is None:
            return ToolResult(
                tool="read_paper_context",
                ok=False,
                summary=f"Saved paper record not found: {paper_id}",
                data={},
            )
        metadata = self._record_metadata(record)
        abstract = record.get("abstract", {})
        markdown = str(record.get("markdown", ""))
        report = str(record.get("report", ""))
        return ToolResult(
            tool="read_paper_context",
            ok=True,
            summary=f"Loaded context for {metadata.get('paper_id', paper_id)}: {metadata.get('title', 'Untitled')}",
            data={
                "metadata": metadata,
                "abstract": abstract,
                "markdown_excerpt": self._truncate(markdown, max_chars),
                "report_excerpt": self._truncate(report, max_chars),
            },
        )

    async def _search_local_records(
        self,
        query: str,
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Run loose keyword search without changing PaperStore semantics."""

        tokens = self._tokenize_local_query(query)
        scored_records: list[tuple[int, str, dict[str, Any]]] = []
        for metadata in records:
            full_record = await self.paper_store.get_paper(str(metadata.get("paper_id", "")))
            searchable_text = self._build_searchable_text(metadata, full_record)
            title_text = str(metadata.get("title", "")).lower()
            source_text = str(metadata.get("source", "")).lower()

            score = 0
            for token in tokens:
                if token not in searchable_text:
                    continue
                score += searchable_text.count(token)
                if token in title_text:
                    score += 5
                if token in source_text:
                    score += 2
            if score > 0:
                scored_records.append((score, str(metadata.get("updated_at", "")), metadata))

        scored_records.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scored_records], tokens

    def _tokenize_local_query(self, query: str) -> list[str]:
        """Tokenize mixed Chinese/English local-library queries for loose matching."""

        lowered = query.lower()
        tokens: list[str] = []
        tokens.extend(re.findall(r"[a-z0-9][a-z0-9_-]*", lowered))

        cjk_stopwords = {
            "\u672c\u5730",
            "\u8bba\u6587",
            "\u8bba\u6587\u5e93",
            "\u76f8\u5173",
            "\u6709\u5173",
            "\u67e5\u627e",
            "\u68c0\u7d22",
            "\u7b5b\u9009",
        }
        for chunk in re.findall(r"[\u4e00-\u9fff]+", lowered):
            if len(chunk) >= 2 and chunk not in cjk_stopwords:
                tokens.append(chunk)
            if len(chunk) > 2:
                tokens.extend(
                    chunk[index : index + 2]
                    for index in range(len(chunk) - 1)
                    if chunk[index : index + 2] not in cjk_stopwords
                )

        deduped: list[str] = []
        for token in tokens:
            cleaned = token.strip()
            if len(cleaned) < 2 or cleaned in deduped:
                continue
            deduped.append(cleaned)
        return deduped or [lowered.strip()]

    def _build_searchable_text(
        self,
        metadata: dict[str, Any],
        full_record: dict[str, Any] | None,
    ) -> str:
        parts = [str(metadata.get(field, "")) for field in ("paper_id", "title", "source", "library_status")]
        if full_record is not None:
            parts.append(json.dumps(full_record.get("abstract", {}), ensure_ascii=False))
            parts.append(str(full_record.get("markdown", ""))[:12000])
            parts.append(str(full_record.get("report", ""))[:12000])
        return " ".join(parts).lower()

    def _summarize_records(
        self,
        records: list[dict[str, Any]],
        *,
        query: str | None = None,
        total_count: int | None = None,
        matched_count: int | None = None,
    ) -> str:
        if not records:
            if query:
                total = 0 if total_count is None else total_count
                return (
                    f"Local paper library has {total} saved paper record(s), "
                    f"but none matched query: {query}."
                )
            return "No saved paper records found."
        if query:
            matched = len(records) if matched_count is None else matched_count
            lines = [
                f"Found {len(records)} of {matched} matching saved paper record(s) "
                f"for query: {query}."
            ]
        else:
            lines = [f"Found {len(records)} saved paper record(s)."]
        for record in records[:5]:
            lines.append(
                f"- {record.get('paper_id', 'N/A')} [{record.get('library_status', 'analyzed')}]: "
                f"{record.get('title', 'Untitled')}"
            )
        return "\n".join(lines)

    def _selected_from_record(self, record: dict[str, Any]) -> dict[str, str]:
        metadata = self._record_metadata(record)
        return {
            "paper_id": str(metadata.get("paper_id", "")),
            "title": str(metadata.get("title", "Untitled")),
            "source": str(metadata.get("source", "N/A")),
            "library_status": str(metadata.get("library_status", "analyzed")),
        }

    def _record_metadata(self, record: dict[str, Any]) -> dict[str, Any]:
        return dict(record.get("metadata", record))

    def _progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)

    def _truncate(self, text: str, limit: int) -> str:
        normalized = text.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."


__all__ = ["PaperToolbox", "register_paper_tools"]
