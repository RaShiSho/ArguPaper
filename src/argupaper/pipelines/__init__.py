"""Workflow-internal stage pipelines."""

from typing import TYPE_CHECKING, Any

__all__ = ["AnalysisChain", "CritiqueChain", "DebateChain", "EvidenceChain"]

if TYPE_CHECKING:
    from argupaper.pipelines.analysis_pipeline import AnalysisChain
    from argupaper.pipelines.critique_pipeline import CritiqueChain
    from argupaper.pipelines.debate_pipeline import DebateChain
    from argupaper.pipelines.evidence_pipeline import EvidenceChain


def __getattr__(name: str) -> Any:
    """Resolve pipeline exports lazily."""

    if name == "AnalysisChain":
        from argupaper.pipelines.analysis_pipeline import AnalysisChain

        return AnalysisChain
    if name == "CritiqueChain":
        from argupaper.pipelines.critique_pipeline import CritiqueChain

        return CritiqueChain
    if name == "DebateChain":
        from argupaper.pipelines.debate_pipeline import DebateChain

        return DebateChain
    if name == "EvidenceChain":
        from argupaper.pipelines.evidence_pipeline import EvidenceChain

        return EvidenceChain
    raise AttributeError(f"module 'argupaper.pipelines' has no attribute {name!r}")