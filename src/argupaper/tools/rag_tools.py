"""RAG workflow-backed tools for Agents."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from argupaper.config import Config
from argupaper.tools.registry import ToolRegistry
from argupaper.tools.schemas import RAGIndexPaperArgs, RAGSearchContextArgs, ToolResult
from argupaper.workflows.errors import ExternalServiceError, InputValidationError
from argupaper.workflows.rag import RAGWorkflow
from argupaper.workflows.rag.options import RAGIndexOptions, RAGSearchOptions
from argupaper.workflows.rag.result import RAGSearchResult

ProgressCallback = Callable[[str], None] | None

CHUNK_TEXT_EXCERPT_CHARS = 1200
METADATA_VALUE_CHARS = 240
METADATA_MAX_KEYS = 16


def register_rag_tools(
    registry: ToolRegistry,
    config: Config,
    *,
    progress_callback: ProgressCallback = None,
) -> None:
    """Register RAG workflow-backed tools."""

    toolbox = RAGToolbox(config, progress_callback=progress_callback)
    registry.register(
        "rag_search_context",
        "Search indexed local paper chunks through RAG and return compact, traceable context.",
        toolbox.search_context,
        args_schema=RAGSearchContextArgs,
    )
    registry.register(
        "rag_index_paper",
        "Index one saved PaperStore paper into the local RAG vector store.",
        toolbox.index_paper,
        args_schema=RAGIndexPaperArgs,
    )


class RAGToolbox:
    """RAG operations exposed as reusable Agent tools."""

    def __init__(self, config: Config, *, progress_callback: ProgressCallback = None) -> None:
        self.config = config
        self.progress_callback = progress_callback

    async def search_context(
        self,
        query: str,
        paper_id: str | None = None,
        top_k: int | None = None,
        section_type: str | None = None,
        score_threshold: float | None = None,
        context_max_chars: int = 12000,
    ) -> ToolResult:
        """Search indexed paper chunks through the RAG workflow facade."""

        if not self.config.rag.enabled:
            return ToolResult(
                tool="rag_search_context",
                ok=False,
                summary="RAG is disabled. Set RAG_ENABLED=true before using rag_search_context.",
                data={},
                warnings=["RAG is disabled."],
                observations={"query": query, "chunks": [], "summary": "RAG is disabled.", "warnings": ["RAG is disabled."]},
            )

        normalized_query = str(query or "").strip()
        if not normalized_query:
            return ToolResult(
                tool="rag_search_context",
                ok=False,
                summary="RAG search query is empty.",
                data={},
                warnings=["RAG search query is empty."],
                observations={"query": "", "chunks": [], "summary": "RAG search query is empty.", "warnings": ["RAG search query is empty."]},
            )

        workflow = RAGWorkflow(self.config)
        try:
            result = await workflow.search(
                RAGSearchOptions(
                    content=normalized_query,
                    paper_id=paper_id,
                    top_k=top_k,
                    section_type=section_type,
                    score_threshold=score_threshold,
                    context_max_chars=context_max_chars,
                ),
                progress_callback=self.progress_callback,
            )
        except (ExternalServiceError, InputValidationError) as exc:
            warning = f"RAG search failed: {type(exc).__name__}: {exc}"
            return ToolResult(
                tool="rag_search_context",
                ok=False,
                summary=warning,
                data={"error_type": type(exc).__name__, "error": str(exc)},
                warnings=[warning],
                observations={"query": normalized_query, "chunks": [], "summary": warning, "warnings": [warning]},
            )
        finally:
            await workflow.close()

        observations = build_rag_search_observations(result)
        summary = _rag_search_summary(result)
        return ToolResult(
            tool="rag_search_context",
            ok=True,
            summary=summary,
            data={
                "query": normalized_query,
                "paper_id": result.paper_id,
                "top_k": result.top_k,
                "rag_context": result.context,
                "rag_chunks": observations["chunks"],
                "warnings": result.warnings,
                "rag_log_path": result.run_log_path,
            },
            warnings=list(result.warnings),
            observations=observations,
        )

    async def index_paper(self, paper_id: str, dry_run: bool = False) -> ToolResult:
        """Index one PaperStore paper through the RAG workflow facade."""

        if not self.config.rag.enabled:
            return ToolResult(
                tool="rag_index_paper",
                ok=False,
                summary="RAG is disabled. Set RAG_ENABLED=true before using rag_index_paper.",
                data={},
                warnings=["RAG is disabled."],
                observations={"paper_id": paper_id, "summary": "RAG is disabled.", "warnings": ["RAG is disabled."]},
            )

        workflow = RAGWorkflow(self.config)
        try:
            result = await workflow.index_paper(
                RAGIndexOptions(paper_id=paper_id, dry_run=dry_run),
                progress_callback=self.progress_callback,
            )
        except (ExternalServiceError, InputValidationError) as exc:
            warning = f"RAG index failed: {type(exc).__name__}: {exc}"
            return ToolResult(
                tool="rag_index_paper",
                ok=False,
                summary=warning,
                data={"paper_id": paper_id, "error_type": type(exc).__name__, "error": str(exc)},
                warnings=[warning],
                observations={"paper_id": paper_id, "summary": warning, "warnings": [warning]},
            )
        finally:
            await workflow.close()

        warnings = list(result.warnings)
        summary = (
            f"Indexed paper {result.paper_id}: {result.chunk_count} chunk(s)"
            if not result.dry_run
            else f"Dry-run indexed paper {result.paper_id}: {result.chunk_count} chunk(s)"
        )
        observations = {
            "paper_id": result.paper_id,
            "chunk_count": result.chunk_count,
            "embedding_dim": result.embedding_dim,
            "skipped_sections": result.skipped_sections,
            "summary": summary,
            "warnings": warnings,
            "rag_log_path": result.run_log_path,
        }
        return ToolResult(
            tool="rag_index_paper",
            ok=True,
            summary=summary,
            data=observations,
            warnings=warnings,
            observations=observations,
        )


def build_rag_search_observations(result: RAGSearchResult) -> dict[str, Any]:
    """Return compact observations for chat logs and responder prompts."""

    chunks = [_compact_chunk(chunk) for chunk in result.chunks]
    summary = _rag_search_summary(result)
    return {
        "query": result.content,
        "paper_id": result.paper_id,
        "top_k": result.top_k,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "context": _truncate_text(result.context, 12000),
        "summary": summary,
        "warnings": list(result.warnings),
        "rag_log_path": result.run_log_path,
    }


def _rag_search_summary(result: RAGSearchResult) -> str:
    scope = f"paper_id={result.paper_id}" if result.paper_id else "all indexed papers"
    if result.chunks:
        return f"RAG retrieved {len(result.chunks)} chunk(s) for query '{result.content}' from {scope}."
    return f"RAG retrieved no chunks for query '{result.content}' from {scope}."


def _compact_chunk(chunk: Any) -> dict[str, Any]:
    page = _page_label(getattr(chunk, "page_start", None), getattr(chunk, "page_end", None))
    return {
        "chunk_id": str(getattr(chunk, "chunk_id", "")),
        "paper_id": str(getattr(chunk, "paper_id", "")),
        "chunk_index": int(getattr(chunk, "chunk_index", 0)),
        "section": getattr(chunk, "section", None) or getattr(chunk, "section_type", None),
        "section_type": getattr(chunk, "section_type", None),
        "page": page,
        "score": float(getattr(chunk, "score", 0.0)),
        "text_excerpt": _truncate_text(str(getattr(chunk, "text", "")), CHUNK_TEXT_EXCERPT_CHARS),
        "metadata": _compact_metadata(getattr(chunk, "metadata", {}) or {}),
    }


def _compact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for index, (key, value) in enumerate(metadata.items()):
        if index >= METADATA_MAX_KEYS:
            break
        if isinstance(value, (str, int, float, bool)) or value is None:
            compact[str(key)] = _truncate_text(str(value), METADATA_VALUE_CHARS) if isinstance(value, str) else value
            continue
        try:
            compact[str(key)] = _truncate_text(json.dumps(value, ensure_ascii=False), METADATA_VALUE_CHARS)
        except (TypeError, ValueError):
            compact[str(key)] = _truncate_text(str(value), METADATA_VALUE_CHARS)
    return compact


def _page_label(page_start: int | None, page_end: int | None) -> str:
    if page_start is None and page_end is None:
        return "unknown"
    if page_end is None or page_end == page_start:
        return str(page_start)
    if page_start is None:
        return str(page_end)
    return f"{page_start}-{page_end}"


def _truncate_text(text: str, limit: int) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return normalized[:limit]
    return normalized[: limit - 3].rstrip() + "..."


__all__ = ["RAGToolbox", "build_rag_search_observations", "register_rag_tools"]
