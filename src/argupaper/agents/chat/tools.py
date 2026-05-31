"""Workflow-backed LangChain tools for the chat agent."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from argupaper.config import Config
from argupaper.memory.paper_store import PaperStore
from argupaper.workflows import AnalyzeOptions, AnalyzeWorkflow, SearchOptions
from argupaper.workflows.papers import PapersOptions, PapersWorkflow
from argupaper.workflows.search import InteractiveSearchWorkflow

ProgressCallback = Optional[Callable[[str], None]]


class ListPapersArgs(BaseModel):
    """Arguments for listing saved papers."""

    query: str | None = Field(default=None, description="Optional local library search text.")
    limit: int = Field(default=20, ge=1, le=50)


class SelectPaperArgs(BaseModel):
    """Arguments for selecting a saved paper."""

    paper: str = Field(description="Paper id, unique id prefix, title, source, or search text.")


class AnalyzePaperArgs(BaseModel):
    """Arguments for analyzing one paper."""

    paper_id: str | None = Field(default=None, description="Paper id. Defaults to selected paper.")
    rounds: int = Field(default=3, ge=1, le=8)


class SearchPapersArgs(BaseModel):
    """Arguments for paper search."""

    query: str
    limit: int = Field(default=10, ge=1, le=50)
    source: str = Field(default="both")


class ReadPaperContextArgs(BaseModel):
    """Arguments for reading selected paper context."""

    paper_id: str | None = Field(default=None, description="Paper id. Defaults to selected paper.")
    max_chars: int = Field(default=6000, ge=500, le=20000)


class ChatToolbox:
    """Build and execute LangChain tools backed by existing workflows."""

    def __init__(self, config: Config, progress_callback: ProgressCallback = None) -> None:
        self.config = config
        self.progress_callback = progress_callback
        self.paper_store = PaperStore(storage_path=config.paper_storage_path)
        self.tools = self._build_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    async def ainvoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one registered tool and normalize failures as observations."""

        tool = self.tools_by_name.get(name)
        if tool is None:
            return {
                "tool": name,
                "ok": False,
                "summary": f"Unknown tool: {name}",
                "data": {"available_tools": sorted(self.tools_by_name)},
            }
        try:
            result = await tool.ainvoke(arguments)
        except Exception as exc:
            return {
                "tool": name,
                "ok": False,
                "summary": f"{name} failed: {exc}",
                "data": {"error_type": type(exc).__name__, "error": str(exc)},
            }
        if isinstance(result, dict):
            return result
        return {"tool": name, "ok": True, "summary": str(result), "data": {}}

    def descriptions(self) -> str:
        """Return compact tool descriptions for prompts."""

        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in sorted(self.tools, key=lambda item: item.name)
        )

    def _build_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                coroutine=self.list_papers,
                name="list_papers",
                description="List or search papers saved in the local PaperStore.",
                args_schema=ListPapersArgs,
            ),
            StructuredTool.from_function(
                coroutine=self.select_paper,
                name="select_paper",
                description="Select a paper by id, unique prefix, title, source, or query.",
                args_schema=SelectPaperArgs,
            ),
            StructuredTool.from_function(
                coroutine=self.analyze_paper,
                name="analyze_paper",
                description="Run the existing AnalyzeWorkflow for a selected or explicit paper id.",
                args_schema=AnalyzePaperArgs,
            ),
            StructuredTool.from_function(
                coroutine=self.search_papers,
                name="search_papers",
                description="Search external academic sources with the existing search workflow.",
                args_schema=SearchPapersArgs,
            ),
            StructuredTool.from_function(
                coroutine=self.read_paper_context,
                name="read_paper_context",
                description="Read metadata, structured summary, markdown excerpt, and report excerpt for a paper.",
                args_schema=ReadPaperContextArgs,
            ),
        ]

    async def list_papers(self, query: str | None = None, limit: int = 20) -> dict[str, Any]:
        """List saved papers through PapersWorkflow."""

        self._progress("Listing saved papers...")
        normalized_query = query.strip() if query else None
        if normalized_query:
            all_records = await self.paper_store.list_papers()
            records, tokens = await self._search_local_records(normalized_query, all_records)
            limited_records = records[:limit]
            return {
                "tool": "list_papers",
                "ok": True,
                "summary": self._summarize_records(
                    limited_records,
                    query=normalized_query,
                    total_count=len(all_records),
                    matched_count=len(records),
                ),
                "data": {
                    "records": limited_records,
                    "count": len(limited_records),
                    "total_count": len(all_records),
                    "matched_count": len(records),
                    "query": normalized_query,
                    "tokens": tokens,
                },
            }

        result = await PapersWorkflow(self.paper_store).run(PapersOptions(limit=limit))
        records = result.records
        return {
            "tool": "list_papers",
            "ok": True,
            "summary": self._summarize_records(records, total_count=len(records)),
            "data": {"records": records, "count": len(records), "total_count": len(records)},
        }

    async def select_paper(self, paper: str) -> dict[str, Any]:
        """Select one paper from PaperStore."""

        self._progress(f"Selecting paper: {paper}...")
        query = paper.strip()
        record = await self.paper_store.get_paper(query)
        if record is not None:
            selected = self._selected_from_record(record)
            return {
                "tool": "select_paper",
                "ok": True,
                "summary": f"Selected paper {selected['paper_id']}: {selected['title']}",
                "data": {"selected_paper": selected, "record": self._record_metadata(record)},
            }

        records = await self.paper_store.search_papers(query)
        exact = [
            item for item in records
            if query.lower() in {
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
                return {
                    "tool": "select_paper",
                    "ok": True,
                    "summary": f"Selected paper {selected['paper_id']}: {selected['title']}",
                    "data": {"selected_paper": selected, "record": self._record_metadata(record)},
                }

        if candidates:
            return {
                "tool": "select_paper",
                "ok": False,
                "summary": "Multiple papers matched. Use a more specific paper id or title.",
                "data": {"candidates": candidates[:8]},
            }
        return {
            "tool": "select_paper",
            "ok": False,
            "summary": f"No saved paper matched: {paper}",
            "data": {},
        }

    async def analyze_paper(self, paper_id: str | None = None, rounds: int = 3) -> dict[str, Any]:
        """Run AnalyzeWorkflow for a converted paper."""

        if not paper_id:
            return {
                "tool": "analyze_paper",
                "ok": False,
                "summary": "No paper is selected. Use /use <paper-id-or-name> first.",
                "data": {},
            }
        self._progress(f"Running AnalyzeWorkflow for {paper_id}...")
        workflow = AnalyzeWorkflow(self.config)
        result = await workflow.run(
            AnalyzeOptions(paper_name=paper_id, rounds=rounds),
            progress_callback=self._progress,
        )
        return {
            "tool": "analyze_paper",
            "ok": True,
            "summary": f"Analysis complete for {result.paper_id}: {result.report_title}",
            "data": {
                "paper_id": result.paper_id,
                "report_title": result.report_title,
                "from_cache": result.from_cache,
                "supplementary_search_used": result.supplementary_search_used,
                "warnings": result.warnings,
                "report_excerpt": self._truncate(result.report_markdown, 3000),
            },
        }

    async def search_papers(self, query: str, limit: int = 10, source: str = "both") -> dict[str, Any]:
        """Run the existing natural-language search workflow."""

        self._progress(f"Searching papers: {query}...")
        workflow = InteractiveSearchWorkflow(self.config)
        result = await workflow.run(
            SearchOptions(
                query=query,
                limit=limit,
                source=source,  # type: ignore[arg-type]
                raw_request=query,
                requested_limit=limit,
                interactive=False,
                limit_overridden=True,
                source_overridden=True,
            ),
            progress_callback=self._progress,
        )
        records = [item.model_dump() for item in result.results]
        return {
            "tool": "search_papers",
            "ok": True,
            "summary": f"Found {len(records)} paper(s) for: {query}",
            "data": {
                "results": records,
                "warnings": result.warnings,
                "trace_dir": result.trace_dir,
                "retrieved_count": result.retrieved_count,
                "filtered_count": result.filtered_count,
            },
        }

    async def read_paper_context(self, paper_id: str | None = None, max_chars: int = 6000) -> dict[str, Any]:
        """Read paper context from PaperStore."""

        if not paper_id:
            return {
                "tool": "read_paper_context",
                "ok": False,
                "summary": "No paper is selected. Use /use <paper-id-or-name> first.",
                "data": {},
            }
        self._progress(f"Reading paper context for {paper_id}...")
        record = await self.paper_store.get_paper(paper_id)
        if record is None:
            return {
                "tool": "read_paper_context",
                "ok": False,
                "summary": f"Saved paper record not found: {paper_id}",
                "data": {},
            }
        metadata = self._record_metadata(record)
        abstract = record.get("abstract", {})
        markdown = str(record.get("markdown", ""))
        report = str(record.get("report", ""))
        return {
            "tool": "read_paper_context",
            "ok": True,
            "summary": f"Loaded context for {metadata.get('paper_id', paper_id)}: {metadata.get('title', 'Untitled')}",
            "data": {
                "metadata": metadata,
                "abstract": abstract,
                "markdown_excerpt": self._truncate(markdown, max_chars),
                "report_excerpt": self._truncate(report, max_chars),
            },
        }

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

    async def _search_local_records(
        self,
        query: str,
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Run chat-local loose keyword search without changing PaperStore."""

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
            "本地",
            "论文",
            "论文库",
            "相关",
            "有关",
            "查找",
            "检索",
            "筛选",
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
        parts = [
            str(metadata.get(field, ""))
            for field in ("paper_id", "title", "source", "library_status")
        ]
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

    def _progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)

    def _truncate(self, text: str, limit: int) -> str:
        normalized = text.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."


def default_paper_id(arguments: dict[str, Any], selected_paper: dict[str, Any] | None) -> dict[str, Any]:
    """Fill paper_id from the selected paper when a tool omitted it."""

    if arguments.get("paper_id") or selected_paper is None:
        return arguments
    filled = dict(arguments)
    filled["paper_id"] = selected_paper.get("paper_id")
    return filled
