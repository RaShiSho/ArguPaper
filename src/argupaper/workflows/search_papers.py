"""Workflow for CLI paper search."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Callable, Optional

from argupaper.config import Config
from argupaper.retrieval import ArXivClient, QueryExpander, SemanticScholarClient
from argupaper.workflows.models import SearchOptions, SearchResult, SearchWorkflowResult

ProgressCallback = Optional[Callable[[str], None]]


class SearchWorkflow:
    """Orchestrates multi-source search for the CLI."""

    def __init__(
        self,
        config: Config,
        expander: Optional[QueryExpander] = None,
        semantic_client: Optional[SemanticScholarClient] = None,
        arxiv_client: Optional[ArXivClient] = None,
    ):
        self.config = config
        self.expander = expander or QueryExpander()
        self.semantic_client = semantic_client or SemanticScholarClient(
            api_key=config.retrieval.semantic_scholar_api_key
        )
        self.arxiv_client = arxiv_client or ArXivClient()

    async def run(
        self,
        options: SearchOptions,
        progress_callback: ProgressCallback = None,
    ) -> SearchWorkflowResult:
        """Run the search workflow."""

        if progress_callback:
            progress_callback("Expanding query...")
        expansion = self.expander.expand(options.query)
        expanded_queries = expansion["expanded_queries"]

        if progress_callback:
            progress_callback("Searching paper sources...")

        source_stats: dict[str, int] = defaultdict(int)
        warnings: list[str] = []
        raw_results: list[SearchResult] = []
        queries_to_run = expanded_queries[:3]
        per_query_limit = min(max(options.limit, 1), self.config.retrieval.max_results)

        for source_name in self._resolve_sources(options.source):
            for query in queries_to_run:
                try:
                    source_results = await self._search_source(source_name, query, per_query_limit)
                    normalized = [SearchResult.model_validate(item) for item in source_results]
                    raw_results.extend(normalized)
                    source_stats[source_name] += len(normalized)
                except Exception as exc:
                    warnings.append(f"{source_name} search failed: {exc}")

        if progress_callback:
            progress_callback("Merging and ranking results...")

        merged_results = self._dedupe_results(raw_results)
        ranked_results = self._rank_results(merged_results, options.query)[: options.limit]

        return SearchWorkflowResult(
            results=ranked_results,
            expanded_queries=expanded_queries,
            source_stats=dict(source_stats),
            warnings=warnings,
        )

    def run_sync(
        self,
        options: SearchOptions,
        progress_callback: ProgressCallback = None,
    ) -> SearchWorkflowResult:
        """Synchronous wrapper used by Typer commands."""

        return asyncio.run(self.run(options, progress_callback))

    def _resolve_sources(self, source: str) -> list[str]:
        if source == "both":
            return ["semantic_scholar", "arxiv"]
        return [source]

    async def _search_source(self, source_name: str, query: str, limit: int) -> list[dict]:
        if source_name == "semantic_scholar":
            return await self.semantic_client.search(query, limit=limit)
        if source_name == "arxiv":
            return await self.arxiv_client.search(query, limit=limit)
        return []

    def _dedupe_results(self, results: list[SearchResult]) -> list[SearchResult]:
        deduped: dict[str, SearchResult] = {}
        alias_to_canonical: dict[str, str] = {}

        for index, result in enumerate(results):
            aliases = [
                alias
                for alias in (
                    self._dedupe_alias("title", result.title),
                    self._dedupe_alias("url", result.url),
                )
                if alias
            ]
            matched_canonicals = {
                alias_to_canonical[alias]
                for alias in aliases
                if alias in alias_to_canonical
            }
            canonical = next(
                (alias_to_canonical[alias] for alias in aliases if alias in alias_to_canonical),
                aliases[0] if aliases else f"result:{index}",
            )

            best_result = result
            for matched_key in matched_canonicals:
                existing = deduped.get(matched_key)
                if existing is not None and existing.citation_count > best_result.citation_count:
                    best_result = existing

            deduped[canonical] = best_result

            merged_keys = matched_canonicals - {canonical}
            for merged_key in merged_keys:
                deduped.pop(merged_key, None)
                for alias, alias_canonical in list(alias_to_canonical.items()):
                    if alias_canonical == merged_key:
                        alias_to_canonical[alias] = canonical

            for alias in aliases:
                alias_to_canonical[alias] = canonical
        return list(deduped.values())

    def _dedupe_alias(self, kind: str, value: str) -> str:
        normalized = " ".join(str(value).strip().casefold().split())
        if not normalized:
            return ""
        return f"{kind}:{normalized}"

    def _rank_results(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        query_tokens = {token for token in query.lower().split() if token}
        current_year = datetime.utcnow().year

        def score(result: SearchResult) -> float:
            title_tokens = set(result.title.lower().split())
            exact_match_weight = len(query_tokens & title_tokens) * 10
            citation_weight = min(result.citation_count, 500) / 10
            recency_weight = max(0, 5 - max(0, current_year - (result.year or current_year)))
            source_weight = 2 if result.source == "semantic_scholar" else 1
            return exact_match_weight + citation_weight + recency_weight + source_weight

        return sorted(results, key=score, reverse=True)
