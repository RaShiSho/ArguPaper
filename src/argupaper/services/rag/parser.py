"""Text parsing helpers for paper RAG chunking."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argupaper.services.pdf import MarkdownCache, MinerUClient
from argupaper.services.pdf.exceptions import CacheError, PDFReadError
from argupaper.workflows.errors import InputValidationError


@dataclass(frozen=True)
class ParsedSection:
    """A section span extracted from a paper text."""

    title: str
    section_type: str
    text: str
    start_offset: int
    end_offset: int
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True)
class ParsedPaperText:
    """Parsed paper text with section spans."""

    source_path: str
    content: str
    content_format: str
    sections: list[ParsedSection]
    metadata: dict[str, Any] = field(default_factory=dict)


class PaperTextParser:
    """Parse local paper PDF, Markdown, or text files for RAG chunking."""

    _SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
    _PDF_SUFFIX = ".pdf"

    _MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
    _NUMBERED_HEADING_RE = re.compile(
        r"^\s*(?:\d+(?:\.\d+)*\.?|[IVXLCM]+\.?)\s+(.+?)\s*$",
        re.IGNORECASE,
    )
    _PAGE_MARKER_RES = [
        re.compile(
            r"^\s*<!--\s*page(?:[_\s-]?(?:number|idx))?\s*[:=]\s*(\d+)\s*-->\s*$",
            re.IGNORECASE,
        ),
        re.compile(r"^\s*\[?\s*page\s+(\d+)\s*\]?\s*$", re.IGNORECASE),
        re.compile(r"^\s*-+\s*page\s+(\d+)\s*-+\s*$", re.IGNORECASE),
        re.compile(r"^\s*page[_\s-]?(?:number|idx)?\s*[:=]\s*(\d+)\s*$", re.IGNORECASE),
    ]

    def __init__(self, pdf_cache_dir: str = "./data/cache") -> None:
        self.pdf_cache_dir = pdf_cache_dir

    def parse_path(self, path: str | Path) -> ParsedPaperText:
        """Parse a local paper path into full text and sections."""

        paper_path = Path(path)
        if not paper_path.exists():
            raise InputValidationError(f"Paper path does not exist: {paper_path}")
        if not paper_path.is_file():
            raise InputValidationError(f"Paper path is not a file: {paper_path}")

        suffix = paper_path.suffix.lower()
        if suffix in self._SUPPORTED_TEXT_SUFFIXES:
            return self._parse_text_file(paper_path)
        if suffix == self._PDF_SUFFIX:
            return self._parse_pdf_file(paper_path)

        raise InputValidationError(
            f"Unsupported paper path type: {paper_path}. Supported suffixes are "
            ".pdf, .md, .markdown, .txt, and .text."
        )

    def parse_text(
        self,
        text: str,
        *,
        source_path: str = "<memory>",
        content_format: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> ParsedPaperText:
        """Parse an in-memory text value into section spans."""

        content = self._normalize_content(text)
        sections = self._extract_sections(content)
        return ParsedPaperText(
            source_path=source_path,
            content=content,
            content_format=content_format,
            sections=sections,
            metadata=dict(metadata or {}),
        )

    def _parse_text_file(self, path: Path) -> ParsedPaperText:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise InputValidationError(f"Paper text file is not valid UTF-8: {path}") from exc
        except OSError as exc:
            raise InputValidationError(f"Cannot read paper text file: {path}, error: {exc}") from exc

        metadata = self._read_paper_store_metadata(path)
        content_format = "markdown" if path.suffix.lower() in {".md", ".markdown"} else "text"
        return self.parse_text(
            content,
            source_path=str(path),
            content_format=content_format,
            metadata=metadata,
        )

    def _parse_pdf_file(self, path: Path) -> ParsedPaperText:
        try:
            cache_key = MinerUClient(api_key="").compute_pdf_hash(path)
        except PDFReadError as exc:
            raise InputValidationError(str(exc)) from exc

        try:
            cache = MarkdownCache(cache_dir=self.pdf_cache_dir)
            content = cache.get(cache_key)
            cache_metadata = cache.get_metadata(cache_key)
        except CacheError as exc:
            raise InputValidationError(f"Cannot read PDF markdown cache: {exc}") from exc

        if content is None:
            raise InputValidationError(
                "PDF has no converted Markdown cache. Run the existing PDF conversion flow "
                f"first, then retry chunking: {path}"
            )

        metadata: dict[str, Any] = {
            "cache_key": cache_key,
            "from_cache": True,
            "source_pdf": str(path),
        }
        if cache_metadata is not None:
            metadata["original_filename"] = cache_metadata.original_filename
            metadata["converted_at"] = cache_metadata.converted_at.isoformat()
            metadata["file_size"] = cache_metadata.file_size

        return self.parse_text(
            content,
            source_path=str(path),
            content_format="markdown",
            metadata=metadata,
        )

    def _read_paper_store_metadata(self, path: Path) -> dict[str, Any]:
        if path.name.lower() != "paper.md":
            return {}

        metadata_path = path.parent / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.exists():
            try:
                raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw_metadata = {}
            if isinstance(raw_metadata, dict):
                metadata.update(raw_metadata)

        metadata.setdefault("paper_id", path.parent.name)
        metadata.setdefault("paper_store_dir", str(path.parent))
        return metadata

    def _extract_sections(self, content: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current_title = "Full Text"
        current_type = "other"
        current_lines: list[str] = []
        current_start_offset = 0
        current_page_start: int | None = None
        current_page_end: int | None = None
        current_page: int | None = None
        offset = 0
        saw_heading = False

        for line in content.splitlines(keepends=True):
            line_start = offset
            offset += len(line)
            marker_page = self._extract_page_marker(line)
            if marker_page is not None:
                current_page = marker_page
                continue

            heading = self._detect_heading(line)
            if heading is not None:
                flushed = self._build_section(
                    current_title,
                    current_type,
                    current_lines,
                    current_start_offset,
                    line_start,
                    current_page_start,
                    current_page_end,
                )
                if flushed is not None:
                    sections.append(flushed)
                current_title, current_type = heading
                current_lines = []
                current_start_offset = offset
                current_page_start = current_page
                current_page_end = current_page
                saw_heading = True
                continue

            if line.strip():
                if current_page_start is None:
                    current_page_start = current_page
                current_page_end = current_page
            current_lines.append(line)

        flushed = self._build_section(
            current_title,
            current_type,
            current_lines,
            current_start_offset,
            len(content),
            current_page_start,
            current_page_end,
        )
        if flushed is not None:
            sections.append(flushed)

        if sections:
            return sections
        if not saw_heading:
            return [
                ParsedSection(
                    title="Full Text",
                    section_type="other",
                    text=content,
                    start_offset=0,
                    end_offset=len(content),
                    page_start=None,
                    page_end=None,
                )
            ]
        return []

    def _build_section(
        self,
        title: str,
        section_type: str,
        lines: list[str],
        start_offset: int,
        end_offset: int,
        page_start: int | None,
        page_end: int | None,
    ) -> ParsedSection | None:
        text = "".join(lines).strip()
        if not text:
            return None
        if page_end is None and page_start is not None:
            page_end = page_start
        return ParsedSection(
            title=title,
            section_type=section_type,
            text=text,
            start_offset=start_offset,
            end_offset=end_offset,
            page_start=page_start,
            page_end=page_end,
        )

    def _detect_heading(self, line: str) -> tuple[str, str] | None:
        stripped = line.strip()
        if not stripped:
            return None

        markdown_match = self._MARKDOWN_HEADING_RE.match(stripped)
        if markdown_match:
            title = self._clean_heading(markdown_match.group(1))
            return title, self._section_type(title)

        numbered_match = self._NUMBERED_HEADING_RE.match(stripped)
        if numbered_match:
            title = self._clean_heading(numbered_match.group(1))
            section_type = self._section_type(title)
            if section_type != "other" or self._looks_like_plain_heading(title):
                return title, section_type
            return None

        title = self._clean_heading(stripped)
        section_type = self._section_type(title)
        if section_type != "other" and self._looks_like_plain_heading(title):
            return title, section_type
        return None

    def _section_type(self, title: str) -> str:
        normalized = self._normalize_heading(title)
        if not normalized:
            return "other"

        if re.search(r"\b(abstract|summary)\b", normalized):
            return "abstract"
        if re.search(r"\b(introduction|background|overview)\b", normalized):
            return "introduction"
        if re.search(r"\b(related work|prior work|literature review)\b", normalized):
            return "related_work"
        if re.search(r"\b(method|methods|methodology|approach|model|architecture)\b", normalized):
            return "method"
        if re.search(
            r"\b(experiment|experiments|evaluation|results|empirical results|analysis)\b",
            normalized,
        ):
            return "experiments"
        if re.search(r"\b(discussion|limitations?|threats to validity)\b", normalized):
            return "discussion"
        if re.search(r"\b(conclusion|conclusions|concluding remarks)\b", normalized):
            return "conclusion"
        if re.search(r"\b(references|bibliography)\b", normalized):
            return "references"
        return "other"

    def _extract_page_marker(self, line: str) -> int | None:
        for pattern in self._PAGE_MARKER_RES:
            match = pattern.match(line.strip())
            if match:
                return int(match.group(1))
        return None

    def _looks_like_plain_heading(self, title: str) -> bool:
        if len(title) > 120:
            return False
        if title.endswith((".", ",", ";", "?", "!")):
            return False
        return bool(re.search(r"[A-Za-z]", title))

    def _clean_heading(self, title: str) -> str:
        cleaned = re.sub(r"\s+", " ", title or "").strip()
        cleaned = cleaned.strip("*_`# ")
        cleaned = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", cleaned)
        cleaned = re.sub(r"^[IVXLCM]+\.?\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip(" :-")

    def _normalize_heading(self, title: str) -> str:
        cleaned = self._clean_heading(title).casefold()
        cleaned = cleaned.replace("&", " and ")
        cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _normalize_content(self, text: str) -> str:
        content = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not content:
            raise InputValidationError("Paper text is empty.")
        return content


__all__ = ["PaperTextParser", "ParsedPaperText", "ParsedSection"]
