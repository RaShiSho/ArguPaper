"""Search agent for natural-language retrieval requests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from argupaper.config import Config
from argupaper.llm import LLMRouter, extract_json_object
from argupaper.workflows.errors import ExternalServiceError, InputValidationError
from argupaper.workflows.models import (
    SearchAgentResult,
    SearchClarification,
    SearchClarificationOption,
    SearchFilters,
    SearchOptions,
    SearchParseResult,
    SearchResult,
)


@dataclass
class SearchClarificationResponse:
    """User response for one clarification step."""

    field: str
    selected_value: str
    selected_label: str


class SearchTraceStore:
    """Persist one search-agent run into a standalone folder."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run_dir(self) -> Path:
        """Create and return a unique run directory."""

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.base_dir / f"{stamp}_{uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_json(self, run_dir: Path, filename: str, payload: object) -> None:
        """Write one JSON payload into the run directory."""

        normalized = self._normalize(payload)
        run_dir.joinpath(filename).write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _normalize(self, payload: object) -> object:
        if hasattr(payload, "model_dump"):
            return payload.model_dump()
        if isinstance(payload, list):
            return [self._normalize(item) for item in payload]
        if isinstance(payload, dict):
            return {str(key): self._normalize(value) for key, value in payload.items()}
        return payload


class SearchRequestParser:
    """Parse one user search request into structured filters."""

    def __init__(self, config: Config, llm_router: LLMRouter | None = None):
        self.config = config
        self.llm_router = llm_router
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts" / "search_agent"
        self.system_prompt = "\n\n".join(
            [
                prompts_dir.joinpath("parse_request_system.txt").read_text(encoding="utf-8").strip(),
                prompts_dir.joinpath("parse_request_schema.txt").read_text(encoding="utf-8").strip(),
            ]
        )

    async def parse(self, raw_request: str) -> SearchParseResult:
        """Parse the raw user request with weak LLM or heuristic fallback."""

        if self.llm_router is not None and self.llm_router.has_provider("weak"):
            try:
                return await self._parse_with_llm(raw_request)
            except (ExternalServiceError, ValueError) as exc:
                fallback = self._parse_with_heuristic(raw_request)
                fallback.parser_notes.append(f"Weak LLM parsing failed; fell back to heuristic parser: {exc}")
                return fallback

        fallback = self._parse_with_heuristic(raw_request)
        fallback.parser_notes.append("Weak LLM provider is not configured; using heuristic parser.")
        return fallback

    async def _parse_with_llm(self, raw_request: str) -> SearchParseResult:
        client = self.llm_router.get_client("weak")
        response = await client.chat(
            system_prompt=self.system_prompt,
            user_prompt=raw_request,
            temperature=min(self.config.model.temperature, 0.3),
            max_tokens=min(self.config.model.max_tokens, 900),
        )
        payload = extract_json_object(response)
        filters = SearchFilters(
            keywords=[str(item).strip() for item in payload.get("keywords", []) if str(item).strip()],
            year_from=payload.get("year_from"),
            year_to=payload.get("year_to"),
            target_count=payload.get("target_count"),
            venue_policy=payload.get("venue_policy"),
            source_preference=payload.get("source_preference"),
        )
        return SearchParseResult(
            raw_request=raw_request,
            filters=filters,
            ambiguities=[
                SearchClarification(
                    field=str(item.get("field", "")).strip(),
                    prompt=str(item.get("prompt", "")).strip(),
                    options=[
                        SearchClarificationOption(
                            value=str(option.get("value", "")).strip(),
                            label=str(option.get("label", "")).strip(),
                        )
                        for option in item.get("options", [])
                        if str(option.get("value", "")).strip() and str(option.get("label", "")).strip()
                    ],
                )
                for item in payload.get("ambiguities", [])
                if str(item.get("field", "")).strip() and str(item.get("prompt", "")).strip()
            ],
            parser="weak_llm",
            parser_notes=[
                str(item).strip()
                for item in payload.get("parser_notes", [])
                if str(item).strip()
            ],
        )

    def _parse_with_heuristic(self, raw_request: str) -> SearchParseResult:
        text = raw_request.strip()
        lowered = text.lower()
        current_year = datetime.now().year

        filters = SearchFilters()
        notes: list[str] = []

        count_match = re.search(r"(\d+)\s*(?:篇|papers?|results?)", lowered)
        if count_match:
            filters.target_count = int(count_match.group(1))

        recent_year_match = re.search(r"近\s*(\d+)\s*年", text)
        if recent_year_match:
            year_window = int(recent_year_match.group(1))
            filters.year_from = current_year - year_window + 1
            filters.year_to = current_year

        if "近两年" in text:
            filters.year_from = current_year - 1
            filters.year_to = current_year
        elif "近三年" in text:
            filters.year_from = current_year - 2
            filters.year_to = current_year

        if "semantic scholar" in lowered:
            filters.source_preference = "semantic_scholar"
        elif "arxiv" in lowered:
            filters.source_preference = "arxiv"

        ambiguities: list[SearchClarification] = []
        if any(token in text for token in ("权威期刊", "高质量论文", "top venue", "authoritative journal")):
            ambiguities.append(self._build_venue_clarification())

        if "期刊" in text and not ambiguities:
            filters.venue_policy = "strict_journal"

        keywords = self._extract_keywords(text)
        if not keywords:
            notes.append("Could not confidently extract search keywords from the request.")
        filters.keywords = keywords

        return SearchParseResult(
            raw_request=raw_request,
            filters=filters,
            ambiguities=ambiguities,
            parser="heuristic",
            parser_notes=notes,
        )

    def _extract_keywords(self, raw_request: str) -> list[str]:
        cleaned = raw_request
        patterns = [
            r"近\s*\d+\s*年",
            r"近两年",
            r"近三年",
            r"\d+\s*(?:篇|papers?|results?)",
            r"权威期刊",
            r"高质量论文",
            r"top venue",
            r"authoritative journal",
            r"期刊论文",
            r"期刊",
            r"论文",
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
        cleaned = re.sub(r"[，,；;。.!?]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")

        quoted = re.findall(r"['\"]([^'\"]+)['\"]", raw_request)
        if quoted:
            return [item.strip() for item in quoted if item.strip()]

        if re.search(r"[A-Za-z]", cleaned):
            ascii_parts = re.findall(r"[A-Za-z][A-Za-z0-9\-_/ ]*[A-Za-z0-9]", cleaned)
            if ascii_parts:
                return [ascii_parts[0].strip()]

        return [cleaned] if cleaned else []

    def _build_venue_clarification(self) -> SearchClarification:
        return SearchClarification(
            field="venue_policy",
            prompt="How should the venue requirement be interpreted?",
            options=[
                SearchClarificationOption(value="strict_journal", label="Journal only"),
                SearchClarificationOption(
                    value="authoritative_publication",
                    label="Journal or top conference",
                ),
                SearchClarificationOption(value="none", label="No venue filter"),
            ],
        )


class SearchAgent:
    """Run parsing, retrieval, filtering, and trace persistence."""

    def __init__(self, config: Config, parser: SearchRequestParser, trace_store: SearchTraceStore):
        self.config = config
        self.parser = parser
        self.trace_store = trace_store

    async def run(
        self,
        options: SearchOptions,
        *,
        search_runner,
        clarification_callback=None,
        progress_callback=None,
    ) -> SearchAgentResult:
        """Execute one search-agent request."""

        raw_request = (options.raw_request or options.query).strip()
        if not raw_request:
            raise InputValidationError("Search request must not be empty.")

        run_dir = self.trace_store.create_run_dir()
        self.trace_store.write_json(
            run_dir,
            "request.json",
            {
                "raw_request": raw_request,
                "options": options.model_dump(),
            },
        )

        if progress_callback:
            progress_callback("Parsing search request...")
        parse_result = await self.parser.parse(raw_request)
        self._apply_cli_overrides(parse_result.filters, options)
        self.trace_store.write_json(run_dir, "parse_result.json", parse_result)

        clarification_responses: list[dict[str, str]] = []
        if parse_result.ambiguities:
            if clarification_callback is None or not options.interactive:
                prompts = "; ".join(item.prompt for item in parse_result.ambiguities)
                raise InputValidationError(
                    f"Ambiguous request requires clarification: {prompts}"
                )

            for ambiguity in parse_result.ambiguities:
                response = clarification_callback(ambiguity)
                clarification_responses.append(
                    {
                        "field": response.field,
                        "selected_value": response.selected_value,
                        "selected_label": response.selected_label,
                    }
                )
                self._apply_clarification(parse_result.filters, response)

        self.trace_store.write_json(run_dir, "clarification.json", clarification_responses)

        if not parse_result.filters.keywords:
            raise InputValidationError("Could not extract search keywords from the request.")

        query = " ".join(parse_result.filters.keywords)
        effective_source = parse_result.filters.source_preference or options.source
        candidate_limit = self._compute_candidate_limit(parse_result.filters, options)

        if progress_callback:
            progress_callback("Retrieving candidate papers...")
        workflow_result = await search_runner(
            SearchOptions(
                query=query,
                limit=candidate_limit,
                source=effective_source,
                verbose=options.verbose,
            )
        )
        self.trace_store.write_json(run_dir, "retrieved_papers.json", workflow_result.results)

        filtered = self._filter_results(workflow_result.results, parse_result.filters)
        warnings = list(workflow_result.warnings)
        warnings.extend(parse_result.parser_notes)
        if parse_result.filters.target_count and len(filtered) < parse_result.filters.target_count:
            warnings.append(
                f"Only {len(filtered)} paper(s) matched the requested filters; "
                f"requested {parse_result.filters.target_count}."
            )

        final_results = filtered[: parse_result.filters.target_count or options.limit]
        self.trace_store.write_json(run_dir, "filtered_papers.json", final_results)

        result = SearchAgentResult(
            results=final_results,
            expanded_queries=workflow_result.expanded_queries,
            source_stats=workflow_result.source_stats,
            warnings=warnings,
            trace_dir=str(run_dir),
            parse_result=parse_result,
            retrieved_count=len(workflow_result.results),
            filtered_count=len(filtered),
            candidate_limit=candidate_limit,
        )
        self.trace_store.write_json(run_dir, "final_result.json", result)
        return result

    def _apply_cli_overrides(self, filters: SearchFilters, options: SearchOptions) -> None:
        if options.limit_overridden and options.requested_limit is not None:
            filters.target_count = options.requested_limit
        elif filters.target_count is None:
            filters.target_count = options.limit

        if options.source_overridden:
            filters.source_preference = options.source
        elif filters.source_preference is None:
            filters.source_preference = options.source

    def _apply_clarification(
        self,
        filters: SearchFilters,
        response: SearchClarificationResponse,
    ) -> None:
        if response.field == "venue_policy":
            filters.venue_policy = None if response.selected_value == "none" else response.selected_value

    def _compute_candidate_limit(self, filters: SearchFilters, options: SearchOptions) -> int:
        target = filters.target_count or options.limit or self.config.retrieval.default_limit
        computed = max(target * 5, 30)
        bounded = min(computed, self.config.search_agent.max_candidates)
        return max(bounded, target)

    def _filter_results(self, results: list[SearchResult], filters: SearchFilters) -> list[SearchResult]:
        filtered: list[SearchResult] = []
        for result in results:
            if filters.year_from is not None and (result.year is None or result.year < filters.year_from):
                continue
            if filters.year_to is not None and (result.year is None or result.year > filters.year_to):
                continue
            if filters.venue_policy == "strict_journal" and not self._is_journal(result):
                continue
            if filters.venue_policy == "authoritative_publication" and not self._is_authoritative_publication(result):
                continue
            filtered.append(result)
        return filtered

    def _is_journal(self, result: SearchResult) -> bool:
        venue = (result.venue or "").strip().lower()
        if not venue or venue == "arxiv":
            return False
        if any(token in venue for token in ("conference", "symposium", "workshop", "neurips", "icml", "cvpr", "acl", "emnlp", "naacl", "iclr", "aaai", "ijcai")):
            return False
        journal_markers = ("journal", "transactions", "letters", "review", "magazine")
        return any(marker in venue for marker in journal_markers)

    def _is_authoritative_publication(self, result: SearchResult) -> bool:
        venue = (result.venue or "").strip().lower()
        if not venue or venue == "arxiv":
            return False
        if self._is_journal(result):
            return True
        top_conference_markers = (
            "neurips",
            "icml",
            "iclr",
            "cvpr",
            "acl",
            "emnlp",
            "naacl",
            "aaai",
            "ijcai",
            "kdd",
            "www",
            "sigir",
        )
        return any(marker in venue for marker in top_conference_markers)
