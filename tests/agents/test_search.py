"""Tests for search-agent parsing and filtering."""

from __future__ import annotations

from pathlib import Path

import pytest

from argupaper.agents.search import SearchAgent, SearchRequestParser, SearchTraceStore
from argupaper.config import Config, DebateConfig, ModelConfig, PDFConfig, RetrievalConfig, SearchAgentConfig
from argupaper.workflows.errors import InputValidationError
from argupaper.workflows.models import SearchOptions, SearchResult, SearchWorkflowResult


def _build_config(tmp_path: Path) -> Config:
    return Config(
        pdf=PDFConfig(api_key=""),
        retrieval=RetrievalConfig(),
        model=ModelConfig(),
        search_agent=SearchAgentConfig(
            trace_path=str(tmp_path / "agent_runs"),
            max_candidates=50,
        ),
        debate=DebateConfig(),
        data_path=str(tmp_path / "data"),
        analyze_enable_retrieval_loop=True,
    )


@pytest.mark.asyncio
async def test_heuristic_parser_extracts_keywords_and_filters(tmp_path: Path) -> None:
    parser = SearchRequestParser(_build_config(tmp_path), llm_router=None)

    result = await parser.parse("agent attack 近两年 10篇论文")

    assert result.filters.keywords == ["agent attack"]
    assert result.filters.target_count == 10
    assert result.filters.year_from is not None
    assert result.parser == "heuristic"


@pytest.mark.asyncio
async def test_search_agent_filters_and_writes_trace(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    parser = SearchRequestParser(config, llm_router=None)
    agent = SearchAgent(config, parser=parser, trace_store=SearchTraceStore(config.search_agent.trace_path))

    async def fake_search_runner(options: SearchOptions) -> SearchWorkflowResult:
        return SearchWorkflowResult(
            results=[
                SearchResult(
                    title="Recent Journal Paper",
                    authors=["A"],
                    year=2026,
                    venue="Journal of AI Research",
                    citation_count=20,
                    url="https://example.com/journal",
                    source="semantic_scholar",
                ),
                SearchResult(
                    title="Old Conference Paper",
                    authors=["B"],
                    year=2021,
                    venue="NeurIPS",
                    citation_count=100,
                    url="https://example.com/conference",
                    source="semantic_scholar",
                ),
            ],
            expanded_queries=[options.query],
            source_stats={"semantic_scholar": 2},
        )

    result = await agent.run(
        SearchOptions(
            query="agent attack 近两年 1篇论文 期刊",
            raw_request="agent attack 近两年 1篇论文 期刊",
            limit=10,
            interactive=False,
        ),
        search_runner=fake_search_runner,
    )

    assert len(result.results) == 1
    assert result.results[0].title == "Recent Journal Paper"
    trace_dir = Path(result.trace_dir)
    assert trace_dir.joinpath("request.json").exists()
    assert trace_dir.joinpath("retrieved_papers.json").exists()
    assert trace_dir.joinpath("filtered_papers.json").exists()
    assert trace_dir.joinpath("final_result.json").exists()


@pytest.mark.asyncio
async def test_search_agent_requires_clarification_for_ambiguous_request(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    parser = SearchRequestParser(config, llm_router=None)
    agent = SearchAgent(config, parser=parser, trace_store=SearchTraceStore(config.search_agent.trace_path))

    async def fake_search_runner(options: SearchOptions) -> SearchWorkflowResult:
        return SearchWorkflowResult()

    with pytest.raises(InputValidationError, match="Ambiguous request requires clarification"):
        await agent.run(
            SearchOptions(
                query="agent attack 权威期刊",
                raw_request="agent attack 权威期刊",
                interactive=False,
            ),
            search_runner=fake_search_runner,
        )
