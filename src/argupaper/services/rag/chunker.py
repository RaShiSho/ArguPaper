"""Chunking pipeline for paper RAG ingestion."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argupaper.services.rag.parser import PaperTextParser, ParsedPaperText, ParsedSection
from argupaper.workflows.errors import InputValidationError


@dataclass(frozen=True)
class PaperChunk:
    """One text chunk ready for embedding or vector indexing."""

    chunk_id: str
    paper_id: str | None
    chunk_index: int
    text: str
    section_title: str
    section_type: str
    page_start: int | None
    page_end: int | None
    source_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PaperChunker:
    """Split parsed paper text into retrieval chunks."""

    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        include_references: bool = False,
        parser: PaperTextParser | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise InputValidationError("chunk_size must be greater than 0.")
        if chunk_overlap < 0:
            raise InputValidationError("chunk_overlap must be greater than or equal to 0.")
        if chunk_overlap >= chunk_size:
            raise InputValidationError("chunk_overlap must be smaller than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.include_references = include_references
        self.parser = parser or PaperTextParser()
        self.max_chars = chunk_size * self.CHARS_PER_TOKEN
        self.overlap_chars = chunk_overlap * self.CHARS_PER_TOKEN

    def chunk_path(self, path: str | Path, paper_id: str | None = None) -> list[PaperChunk]:
        """Parse and chunk a local paper path."""

        parsed = self.parser.parse_path(path)
        return self.chunk_parsed(parsed, paper_id=paper_id)

    def chunk_text(
        self,
        text: str,
        *,
        source_path: str = "<memory>",
        paper_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[PaperChunk]:
        """Chunk an in-memory paper text."""

        parsed = self.parser.parse_text(
            text,
            source_path=source_path,
            content_format="text",
            metadata=metadata,
        )
        return self.chunk_parsed(parsed, paper_id=paper_id)

    def chunk_parsed(
        self,
        parsed: ParsedPaperText,
        paper_id: str | None = None,
    ) -> list[PaperChunk]:
        """Chunk an already parsed paper text."""

        resolved_paper_id = self._resolve_paper_id(parsed, paper_id)
        source_key = self._source_key(parsed, resolved_paper_id)
        chunks: list[PaperChunk] = []

        for section in parsed.sections:
            if section.section_type == "references" and not self.include_references:
                continue

            for chunk_text in self._split_section_text(section.text):
                chunk_index = len(chunks)
                chunks.append(
                    PaperChunk(
                        chunk_id=self._chunk_id(source_key, resolved_paper_id, chunk_index),
                        paper_id=resolved_paper_id,
                        chunk_index=chunk_index,
                        text=chunk_text,
                        section_title=section.title,
                        section_type=section.section_type,
                        page_start=section.page_start,
                        page_end=section.page_end,
                        source_path=parsed.source_path,
                        metadata=self._chunk_metadata(parsed, section),
                    )
                )

        return chunks

    def _split_section_text(self, text: str) -> list[str]:
        cleaned = self._clean_text(text)
        if not cleaned:
            return []

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", cleaned)]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]
        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            if len(paragraph) > self.max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_long_text(paragraph))
                continue

            if not current:
                current = paragraph
                continue

            candidate = f"{current}\n\n{paragraph}"
            if len(candidate) <= self.max_chars:
                current = candidate
                continue

            chunks.append(current)
            overlap = self._overlap_tail(current)
            if overlap and len(f"{overlap}\n\n{paragraph}") <= self.max_chars:
                current = f"{overlap}\n\n{paragraph}"
            else:
                current = paragraph

        if current:
            chunks.append(current)
        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        step = max(1, self.max_chars - self.overlap_chars)
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.max_chars)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start += step
        return chunks

    def _overlap_tail(self, text: str) -> str:
        if self.overlap_chars <= 0:
            return ""
        tail = text[-self.overlap_chars :]
        boundary = tail.find("\n\n")
        if boundary > 0:
            tail = tail[boundary + 2 :]
        return tail.strip()

    def _clean_text(self, text: str) -> str:
        normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _resolve_paper_id(
        self,
        parsed: ParsedPaperText,
        explicit_paper_id: str | None,
    ) -> str | None:
        if explicit_paper_id is not None and explicit_paper_id.strip():
            return explicit_paper_id.strip()

        metadata_paper_id = parsed.metadata.get("paper_id")
        if metadata_paper_id is not None and str(metadata_paper_id).strip():
            return str(metadata_paper_id).strip()

        source_path = Path(parsed.source_path)
        if source_path.name.lower() == "paper.md" and source_path.parent.name:
            return source_path.parent.name
        return None

    def _source_key(self, parsed: ParsedPaperText, paper_id: str | None) -> str:
        if paper_id:
            return paper_id
        digest = hashlib.sha256(
            f"{parsed.source_path}\n{parsed.content}".encode("utf-8")
        ).hexdigest()
        return digest[:16]

    def _chunk_id(self, source_key: str, paper_id: str | None, chunk_index: int) -> str:
        if paper_id:
            return f"{paper_id}:{chunk_index:05d}"
        return f"{source_key}:{chunk_index:05d}"

    def _chunk_metadata(
        self,
        parsed: ParsedPaperText,
        section: ParsedSection,
    ) -> dict[str, Any]:
        metadata = dict(parsed.metadata)
        metadata["content_format"] = parsed.content_format
        metadata["section_title"] = section.title
        metadata["section_type"] = section.section_type
        return metadata


__all__ = ["PaperChunk", "PaperChunker"]
