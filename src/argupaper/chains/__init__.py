"""Chain exports for the analysis pipeline."""

from typing import TYPE_CHECKING, Any

__all__ = [
    "AnalysisChain",
    "DebateChain",
    "EvidenceChain",
]

if TYPE_CHECKING:
    from argupaper.chains.analysis import AnalysisChain
    from argupaper.chains.debate import DebateChain
    from argupaper.chains.evidence import EvidenceChain


def __getattr__(name: str) -> Any:
    """Resolve chain exports lazily to avoid package import cycles."""

    if name == "AnalysisChain":
        from argupaper.chains.analysis import AnalysisChain

        return AnalysisChain
    if name == "DebateChain":
        from argupaper.chains.debate import DebateChain

        return DebateChain
    if name == "EvidenceChain":
        from argupaper.chains.evidence import EvidenceChain

        return EvidenceChain
    raise AttributeError(f"module 'argupaper.chains' has no attribute {name!r}")
