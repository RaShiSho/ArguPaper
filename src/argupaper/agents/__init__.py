"""Agent definitions for multi-agent debate system."""

from typing import TYPE_CHECKING, Any

__all__ = [
    "AgentBase",
    "SearchAgent",
    "SearchClarificationResponse",
    "SearchRequestParser",
    "SupportAgent",
    "SkepticAgent",
    "ComparatorAgent",
    "EvidenceAgent",
]

if TYPE_CHECKING:
    from argupaper.agents.base import AgentBase
    from argupaper.agents.comparator import ComparatorAgent
    from argupaper.agents.evidence import EvidenceAgent
    from argupaper.agents.search import (
        SearchAgent,
        SearchClarificationResponse,
        SearchRequestParser,
    )
    from argupaper.agents.skeptic import SkepticAgent
    from argupaper.agents.support import SupportAgent


def __getattr__(name: str) -> Any:
    """Resolve agent exports lazily to avoid package import cycles."""

    if name == "AgentBase":
        from argupaper.agents.base import AgentBase

        return AgentBase
    if name == "SearchAgent":
        from argupaper.agents.search import SearchAgent

        return SearchAgent
    if name == "SearchClarificationResponse":
        from argupaper.agents.search import SearchClarificationResponse

        return SearchClarificationResponse
    if name == "SearchRequestParser":
        from argupaper.agents.search import SearchRequestParser

        return SearchRequestParser
    if name == "SupportAgent":
        from argupaper.agents.support import SupportAgent

        return SupportAgent
    if name == "SkepticAgent":
        from argupaper.agents.skeptic import SkepticAgent

        return SkepticAgent
    if name == "ComparatorAgent":
        from argupaper.agents.comparator import ComparatorAgent

        return ComparatorAgent
    if name == "EvidenceAgent":
        from argupaper.agents.evidence import EvidenceAgent

        return EvidenceAgent
    raise AttributeError(f"module 'argupaper.agents' has no attribute {name!r}")
