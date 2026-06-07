"""Best-effort paper title extraction from converted Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from argupaper.services.llm import LLMRouter, extract_json_object

TITLE_SOURCE_MARKDOWN_HEADING = "markdown_heading"
TITLE_SOURCE_MARKDOWN_FRONT_MATTER = "markdown_front_matter"
TITLE_SOURCE_LLM = "llm"
TITLE_SOURCE_FILENAME_FALLBACK = "filename_fallback"

SECTION_HEADINGS = {
    "abstract",
    "introduction",
    "background",
    "overview",
    "keywords",
    "contents",
    "table of contents",
    "related work",
    "references",
    "acknowledgements",
    "acknowledgments",
}


@dataclass(frozen=True)
class PaperTitleResult:
    """Resolved paper title and provenance metadata."""

    title: str
    source: str
    confidence: float
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _LocalTitleCandidate:
    title: str
    source: str
    confidence: float


class PaperTitleResolver:
    """Resolve a real paper title before writing records to PaperStore."""

    def __init__(self, *, front_matter_lines: int = 80, llm_context_chars: int = 6000) -> None:
        self.front_matter_lines = front_matter_lines
        self.llm_context_chars = llm_context_chars

    async def resolve(
        self,
        markdown: str,
        source_label: str,
        llm_router: LLMRouter | None = None,
    ) -> PaperTitleResult:
        """Resolve the most likely title using local parsing, then optional LLM fallback."""

        fallback_title = self._fallback_title(source_label)
        warnings: list[str] = []
        local_candidate = self._resolve_local(markdown)
        if local_candidate is not None and not self._should_try_llm(local_candidate.title, fallback_title):
            return PaperTitleResult(
                title=local_candidate.title,
                source=local_candidate.source,
                confidence=local_candidate.confidence,
            )

        llm_result = await self._resolve_with_llm(
            markdown=markdown,
            source_label=source_label,
            fallback_title=fallback_title,
            llm_router=llm_router,
        )
        if llm_result is not None and llm_result.title.strip():
            if local_candidate is not None:
                warnings.append(
                    f"Local title candidate '{local_candidate.title}' was replaced by LLM output."
                )
            return PaperTitleResult(
                title=llm_result.title,
                source=llm_result.source,
                confidence=llm_result.confidence,
                warnings=warnings + llm_result.warnings,
            )
        if llm_result is not None:
            warnings.extend(llm_result.warnings)

        if local_candidate is not None:
            return PaperTitleResult(
                title=local_candidate.title,
                source=local_candidate.source,
                confidence=local_candidate.confidence,
                warnings=warnings,
            )

        return PaperTitleResult(
            title=fallback_title,
            source=TITLE_SOURCE_FILENAME_FALLBACK,
            confidence=0.2,
            warnings=warnings
            + ["Paper title could not be resolved from Markdown; used filename fallback."],
        )

    def _resolve_local(self, markdown: str) -> _LocalTitleCandidate | None:
        lines = markdown.splitlines()[: self.front_matter_lines]
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                continue
            heading = self._extract_h1(stripped)
            if heading is None:
                continue
            if self._is_valid_title(heading):
                return _LocalTitleCandidate(
                    title=heading,
                    source=TITLE_SOURCE_MARKDOWN_HEADING,
                    confidence=0.95,
                )

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                heading_text = stripped.lstrip("#").strip().lower()
                if heading_text in SECTION_HEADINGS:
                    break
                continue
            candidate = self._clean_candidate(stripped)
            if candidate.casefold() in SECTION_HEADINGS:
                break
            if self._is_valid_title(candidate):
                return _LocalTitleCandidate(
                    title=candidate,
                    source=TITLE_SOURCE_MARKDOWN_FRONT_MATTER,
                    confidence=0.75,
                )
        return None

    async def _resolve_with_llm(
        self,
        *,
        markdown: str,
        source_label: str,
        fallback_title: str,
        llm_router: LLMRouter | None,
    ) -> PaperTitleResult | None:
        alias = self._select_llm_alias(llm_router)
        if alias is None or llm_router is None:
            return None

        context = markdown[: self.llm_context_chars]
        if not context.strip():
            return None

        try:
            client = llm_router.get_client(alias)
            response = await client.chat(
                system_prompt=(
                    "You extract exact research paper titles from converted Markdown. "
                    "Return only JSON with keys title and confidence. Do not invent a title."
                ),
                user_prompt=(
                    "Find the real paper title from the Markdown front matter. "
                    "Ignore authors, affiliations, emails, section headings, figures, tables, "
                    "and the PDF filename unless no better title exists.\n\n"
                    f"PDF filename or source label: {source_label}\n"
                    f"Filename fallback: {fallback_title}\n\n"
                    "Markdown excerpt:\n"
                    f"{context}"
                ),
                temperature=0.0,
                max_tokens=180,
            )
            payload = extract_json_object(response)
            title = self._clean_candidate(str(payload.get("title", "")))
            confidence = self._coerce_confidence(payload.get("confidence"), default=0.65)
        except Exception as exc:  # noqa: BLE001 - title resolution must not block storage
            return PaperTitleResult(
                title="",
                source=TITLE_SOURCE_LLM,
                confidence=0.0,
                warnings=[f"LLM title extraction failed: {type(exc).__name__}: {exc}"],
            )

        if not self._is_valid_title(title):
            return None
        return PaperTitleResult(
            title=title,
            source=TITLE_SOURCE_LLM,
            confidence=confidence,
        )

    def _select_llm_alias(self, llm_router: LLMRouter | None) -> str | None:
        if llm_router is None:
            return None
        if llm_router.has_provider("weak"):
            return "weak"
        if llm_router.has_provider("default"):
            return "default"
        return None

    def _extract_h1(self, line: str) -> str | None:
        match = re.match(r"^#(?!#)\s+(.+?)\s*$", line)
        if match is None:
            return None
        return self._clean_candidate(match.group(1))

    def _clean_candidate(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"^#+\s*", "", cleaned)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = cleaned.strip(" \t\r\n#*`_")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def _is_valid_title(self, candidate: str) -> bool:
        normalized = candidate.strip()
        lowered = normalized.casefold()
        if len(normalized) < 4 or len(normalized) > 240:
            return False
        if lowered in SECTION_HEADINGS:
            return False
        if lowered.startswith(("figure ", "fig. ", "table ", "appendix ")):
            return False
        if normalized.startswith(("!", "|", "-", "*", ">", "<summary", "<details")):
            return False
        if "@" in normalized or "http://" in lowered or "https://" in lowered:
            return False
        if re.search(r"\b(arxiv|doi)\s*[:\uff1a]", lowered):
            return False
        if re.fullmatch(r"[\W\d_]+", normalized):
            return False
        return True

    def _should_try_llm(self, title: str, fallback_title: str) -> bool:
        normalized_title = self._normalize_compare_text(title)
        normalized_fallback = self._normalize_compare_text(fallback_title)
        if not normalized_title or normalized_title != normalized_fallback:
            return False
        compact = re.sub(r"[^A-Za-z0-9]", "", title)
        return len(compact) <= 12 or compact.isupper()

    def _fallback_title(self, source_label: str) -> str:
        source_path = Path(str(source_label or "").strip())
        fallback = source_path.stem or str(source_label or "").strip() or "Untitled Paper"
        return self._clean_candidate(fallback) or "Untitled Paper"

    def _normalize_compare_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    def _coerce_confidence(self, value: object, *, default: float) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return default
        if confidence > 1:
            confidence = confidence / 100
        return max(0.0, min(confidence, 1.0))


__all__ = [
    "PaperTitleResolver",
    "PaperTitleResult",
    "TITLE_SOURCE_FILENAME_FALLBACK",
    "TITLE_SOURCE_LLM",
    "TITLE_SOURCE_MARKDOWN_FRONT_MATTER",
    "TITLE_SOURCE_MARKDOWN_HEADING",
]
