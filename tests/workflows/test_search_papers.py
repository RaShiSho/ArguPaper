"""Tests for search workflow result handling."""

from __future__ import annotations

from argupaper.config import Config, DebateConfig, ModelConfig, PDFConfig, RetrievalConfig, SearchAgentConfig
from argupaper.workflows.models import SearchResult
from argupaper.workflows.search_papers import SearchWorkflow


def _build_config() -> Config:
    return Config(
        pdf=PDFConfig(api_key=""),
        retrieval=RetrievalConfig(),
        model=ModelConfig(),
        search_agent=SearchAgentConfig(trace_path=".pytest/cache/agent_runs"),
        debate=DebateConfig(),
        data_path=".pytest/cache/data",
        analyze_enable_retrieval_loop=True,
    )


def test_search_workflow_dedupes_cross_source_results_by_title() -> None:
    workflow = SearchWorkflow(_build_config())

    deduped = workflow._dedupe_results(
        [
            SearchResult(
                title="Attention Is All You Need",
                authors=["A"],
                year=2017,
                venue="NeurIPS",
                citation_count=1000,
                url="https://arxiv.org/abs/1706.03762",
                source="arxiv",
            ),
            SearchResult(
                title=" Attention   Is All You Need ",
                authors=["B"],
                year=2017,
                venue="NeurIPS",
                citation_count=2000,
                url="https://www.semanticscholar.org/paper/attention",
                source="semantic_scholar",
            ),
        ]
    )

    assert len(deduped) == 1
    assert deduped[0].citation_count == 2000
    assert deduped[0].source == "semantic_scholar"
