"""Build LLM-ready context strings from retrieved chunks."""

from __future__ import annotations

from dataclasses import dataclass

from argupaper.services.rag.retriever import RetrievedChunk
from argupaper.workflows.errors import InputValidationError


@dataclass(frozen=True)
class ContextBuilder:
    """Render retrieved chunks into a bounded LLM context string."""

    max_chars: int = 12000
    restore_local_order: bool = False

    def __post_init__(self) -> None:
        if self.max_chars <= 0:
            raise InputValidationError("ContextBuilder.max_chars must be greater than 0.")

    def build_context(self, chunks: list[RetrievedChunk]) -> str:
        """Build a traceable context string for LLM prompts."""

        ordered_chunks = self._order_chunks(self._dedupe_chunks(chunks))
        parts: list[str] = []
        used_chars = 0

        for chunk in ordered_chunks:
            block = self._chunk_block(chunk)
            separator_len = 2 if parts else 0
            if used_chars + separator_len + len(block) <= self.max_chars:
                parts.append(block)
                used_chars += separator_len + len(block)
                continue

            remaining = self.max_chars - used_chars - separator_len
            if remaining <= 0:
                break
            truncated = self._truncate_block(block, remaining)
            if truncated:
                parts.append(truncated)
            break

        return "\n\n".join(parts).strip()

    def _dedupe_chunks(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        by_id: dict[str, RetrievedChunk] = {}
        for chunk in chunks:
            existing = by_id.get(chunk.chunk_id)
            if existing is None or chunk.score > existing.score:
                by_id[chunk.chunk_id] = chunk
        return list(by_id.values())

    def _order_chunks(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if self.restore_local_order:
            return sorted(
                chunks,
                key=lambda chunk: (chunk.paper_id, self._section_key(chunk), chunk.chunk_index),
            )
        return sorted(chunks, key=lambda chunk: chunk.score, reverse=True)

    def _chunk_block(self, chunk: RetrievedChunk) -> str:
        return f"{self._source_marker(chunk)}\n{chunk.text.strip()}"

    def _source_marker(self, chunk: RetrievedChunk) -> str:
        return (
            f"[chunk_id={chunk.chunk_id}, "
            f"paper={chunk.paper_id}, "
            f"section={chunk.section or chunk.section_type or 'unknown'}, "
            f"page={self._page_label(chunk)}, "
            f"score={chunk.score:.4f}]"
        )

    def _page_label(self, chunk: RetrievedChunk) -> str:
        if chunk.page_start is None and chunk.page_end is None:
            return "unknown"
        if chunk.page_end is None or chunk.page_end == chunk.page_start:
            return str(chunk.page_start)
        if chunk.page_start is None:
            return str(chunk.page_end)
        return f"{chunk.page_start}-{chunk.page_end}"

    def _section_key(self, chunk: RetrievedChunk) -> str:
        return chunk.section_type or chunk.section or ""

    def _truncate_block(self, block: str, limit: int) -> str:
        if limit <= 0:
            return ""
        if len(block) <= limit:
            return block
        if limit <= 3:
            return block[:limit]
        return block[: limit - 3].rstrip() + "..."


__all__ = ["ContextBuilder"]
