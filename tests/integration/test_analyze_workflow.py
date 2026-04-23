"""Integration tests for the analyze workflow mainline."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from argupaper.agents.message import AgentMessage, DebateState
from argupaper.chains.debate import DebateChain
from argupaper.config import Config, DebateConfig, ModelConfig, PDFConfig, RetrievalConfig, SearchAgentConfig
from argupaper.judge.consensus import ConsensusDetector
from argupaper.output.report import ReportGenerator
from argupaper.pdf.types import ConversionResult, TaskStatus
from argupaper.workflows.analyze_paper import AnalyzeWorkflow
from argupaper.workflows.models import AnalyzeOptions, SearchResult, SearchWorkflowResult


def _build_config(tmp_path: Path) -> Config:
    return Config(
        pdf=PDFConfig(api_key="test-key", cache_dir=str(tmp_path / "cache")),
        retrieval=RetrievalConfig(),
        model=ModelConfig(),
        search_agent=SearchAgentConfig(trace_path=str(tmp_path / "trace")),
        debate=DebateConfig(max_rounds=3),
        data_path=str(tmp_path / "data"),
        analyze_enable_retrieval_loop=True,
    )


@pytest.fixture
def workspace_dir() -> Path:
    """Create a manual workspace without relying on pytest tmp_path."""

    root = Path.cwd() / "test_workspace"
    root.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="analyze_", dir=root))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class StubPipeline:
    """Simple pipeline stub returning canned markdown."""

    def __init__(self) -> None:
        self.closed = False

    async def process(self, pdf_path: Path, force_reconvert: bool = False) -> ConversionResult:
        return ConversionResult(
            status=TaskStatus.SUCCESS,
            markdown=(
                "# Test Paper\n\n"
                "## Abstract\nA compact abstract.\n\n"
                "## Method\nMethod details.\n\n"
                "## Evaluation\nCIFAR-10 accuracy baseline ablation.\n"
            ),
            cache_key="paper-xyz",
            from_cache=force_reconvert is False,
        )

    async def close(self) -> None:
        self.closed = True


class StubExtractor:
    """Deterministic extractor used by integration tests."""

    async def extract_abstract(self, markdown: str) -> dict[str, str]:
        return {
            "problem": "robust image classification under distribution shift",
            "method": "regularized contrastive training with calibration",
            "experiment": "evaluated on CIFAR-10 with accuracy and robustness metrics",
            "conclusion": "the method improves robustness with moderate cost",
        }

    async def extract_method(self, markdown: str) -> dict[str, object]:
        return {
            "details": "regularized contrastive training with calibration",
            "assumptions": ["data augmentation approximates target shift."],
            "limitations": "The paper does not fully discuss deployment cost.",
        }

    async def extract_experiments(self, markdown: str) -> dict[str, object]:
        return {
            "datasets": ["CIFAR-10"],
            "metrics": ["accuracy", "robust accuracy"],
            "sample_sizes": ["50000"],
            "has_baseline": True,
            "has_ablation": True,
        }


class StubAnalysisChain:
    """Deterministic analysis output."""

    async def run(self, paper_markdown: str) -> dict[str, object]:
        return {
            "title": "Test Paper",
            "overview": "the paper studies robust image classification under distribution shift",
            "research_problem": "robust image classification under distribution shift",
            "method_analysis": "regularized contrastive training with calibration",
            "technical_route": "regularized contrastive training with calibration",
            "key_claims": ["the method improves robustness without a large accuracy drop"],
            "weakness_hints": ["The deployment cost is not fully quantified."],
        }


class StubEvidenceChain:
    """Configurable evidence output for workflow tests."""

    def __init__(
        self,
        *,
        needs_supplementary_search: bool,
        has_baseline: bool = True,
        has_ablation: bool = True,
    ) -> None:
        self.needs_supplementary_search = needs_supplementary_search
        self.has_baseline = has_baseline
        self.has_ablation = has_ablation

    async def run(self, paper_markdown: str) -> dict[str, object]:
        return {
            "evidence_table": [
                {
                    "dataset": "CIFAR-10",
                    "metric": "accuracy, robust accuracy",
                    "support": "Referenced in evaluation section",
                }
            ],
            "datasets": ["CIFAR-10"],
            "metrics": ["accuracy", "robust accuracy"],
            "sample_sizes": ["50000"],
            "has_baseline": self.has_baseline,
            "has_ablation": self.has_ablation,
            "weakness_analysis": "Evidence coverage looks reasonable.",
            "contradictions": [],
            "unsupported_claims": [],
            "needs_supplementary_search": self.needs_supplementary_search,
        }


class StubSearchWorkflow:
    """Supplementary retrieval stub."""

    def __init__(self, *, raise_error: bool = False) -> None:
        self.raise_error = raise_error

    async def run(self, options) -> SearchWorkflowResult:
        if self.raise_error:
            raise RuntimeError("supplementary lookup unavailable")
        return SearchWorkflowResult(
            results=[
                SearchResult(
                    title="Comparison Paper",
                    authors=["A. Author"],
                    year=2024,
                    venue="Journal of Robust ML",
                    citation_count=12,
                    url="https://example.com/comparison",
                    source="semantic_scholar",
                )
            ],
            expanded_queries=[options.query],
            source_stats={"semantic_scholar": 1},
            warnings=["supplementary retrieval used cached semantic scholar ranking"],
        )


class StubPaperStore:
    """In-memory paper store for workflow integration tests."""

    def __init__(self) -> None:
        self.saved: dict[str, dict[str, object]] = {}

    async def save_paper(self, paper_id: str, knowledge: dict) -> None:
        self.saved[paper_id] = knowledge


class ExplodingDebateChain:
    """Debate chain stub that forces workflow degradation."""

    max_rounds = 1

    async def run(self, initial_context: dict) -> DebateState:
        raise RuntimeError("debate engine unavailable")


class CapturingDebateChain:
    """Debate chain stub used to verify rounds propagation."""

    def __init__(self) -> None:
        self.max_rounds = 1

    async def run(self, initial_context: dict) -> DebateState:
        support = f"round-budget:{self.max_rounds}"
        skeptic = f"skeptic-reviewed:{self.max_rounds}"
        return DebateState(
            round=1,
            messages=[
                AgentMessage(agent_role="support", round=1, content=support),
                AgentMessage(agent_role="skeptic", round=1, content=skeptic),
            ],
            current_claims=["budget propagation"],
            consensus_reached=False,
            support_positions=[support],
            skeptic_positions=[skeptic],
        )


def _build_workflow(
    tmp_path: Path,
    *,
    evidence_chain: StubEvidenceChain,
    debate_chain,
    search_workflow: StubSearchWorkflow,
) -> AnalyzeWorkflow:
    return AnalyzeWorkflow(
        _build_config(tmp_path),
        extractor=StubExtractor(),
        analysis_chain=StubAnalysisChain(),
        evidence_chain=evidence_chain,
        debate_chain=debate_chain,
        consensus_detector=ConsensusDetector(),
        report_generator=ReportGenerator(),
        paper_store=StubPaperStore(),
        search_workflow=search_workflow,
        pipeline_factory=StubPipeline,
    )


@pytest.mark.asyncio
async def test_analyze_workflow_happy_path_includes_debate_judge_and_retrieval(
    workspace_dir: Path,
) -> None:
    workflow = _build_workflow(
        workspace_dir,
        evidence_chain=StubEvidenceChain(needs_supplementary_search=True),
        debate_chain=DebateChain(max_rounds=4),
        search_workflow=StubSearchWorkflow(),
    )

    result = await workflow.run(
        AnalyzeOptions(
            paper_path=workspace_dir / "paper.pdf",
            rounds=4,
        )
    )

    assert "## Debate Summary" in result.report_markdown
    assert "## Consensus vs Disagreement" in result.report_markdown
    assert "## Method Comparison" in result.report_markdown
    assert "Comparison Paper" in result.report_markdown
    assert "Confidence:" in result.report_markdown
    assert result.supplementary_search_used is True
    assert "supplementary retrieval used cached semantic scholar ranking" in result.warnings


@pytest.mark.asyncio
async def test_analyze_workflow_degrades_gracefully_when_retrieval_and_debate_fail(
    workspace_dir: Path,
) -> None:
    workflow = _build_workflow(
        workspace_dir,
        evidence_chain=StubEvidenceChain(
            needs_supplementary_search=True,
            has_baseline=False,
            has_ablation=False,
        ),
        debate_chain=ExplodingDebateChain(),
        search_workflow=StubSearchWorkflow(raise_error=True),
    )

    result = await workflow.run(
        AnalyzeOptions(
            paper_path=workspace_dir / "paper.pdf",
            rounds=2,
        )
    )

    assert "## Warnings" in result.report_markdown
    assert "Supplementary retrieval failed" in result.report_markdown
    assert "Debate failed" in result.report_markdown
    assert any("Supplementary retrieval failed" in item for item in result.warnings)
    assert any("Debate failed" in item for item in result.warnings)
    assert "## Confidence Score" in result.report_markdown


@pytest.mark.asyncio
async def test_analyze_workflow_passes_rounds_to_debate_chain(workspace_dir: Path) -> None:
    debate_chain = CapturingDebateChain()
    workflow = _build_workflow(
        workspace_dir,
        evidence_chain=StubEvidenceChain(needs_supplementary_search=False),
        debate_chain=debate_chain,
        search_workflow=StubSearchWorkflow(),
    )

    result = await workflow.run(
        AnalyzeOptions(
            paper_path=workspace_dir / "paper.pdf",
            rounds=5,
        )
    )

    assert debate_chain.max_rounds == 5
    assert "round-budget:5" in result.report_markdown
