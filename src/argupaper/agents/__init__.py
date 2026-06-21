"""Agent definitions for multi-agent research discussion."""

from typing import TYPE_CHECKING, Any

__all__ = [
    "AgentBase",
    "AgentConfig",
    "AgentMessage",
    "ComparatorAgent",
    "DebateState",
    "EvidenceAgent",
    "SearchClarificationResponse",
    "SearchRequestParser",
    "SearchRequestRunner",
    "SkepticAgent",
    "SupportAgent",
]

if TYPE_CHECKING:
    from argupaper.agents.models import AgentMessage, DebateState
    from argupaper.agents.roles.comparator import ComparatorAgent
    from argupaper.agents.roles.evidence import EvidenceAgent
    from argupaper.agents.roles.skeptic import SkepticAgent
    from argupaper.agents.roles.support import SupportAgent
    from argupaper.agents.runtime.base import AgentBase, AgentConfig
    from argupaper.workflows.search.parser import (
        SearchClarificationResponse,
        SearchRequestParser,
        SearchRequestRunner,
    )


def __getattr__(name: str) -> Any:
    """Resolve agent exports lazily to avoid package import cycles."""

    if name in {"AgentBase", "AgentConfig"}:
        from argupaper.agents.runtime import base

        return getattr(base, name)
    if name in {"AgentMessage", "DebateState"}:
        from argupaper.agents import models

        return getattr(models, name)
    if name in {"SupportAgent", "SkepticAgent", "ComparatorAgent", "EvidenceAgent"}:
        from argupaper.agents import roles

        return getattr(roles, name)
    if name in {"SearchClarificationResponse", "SearchRequestParser", "SearchRequestRunner"}:
        from argupaper.workflows.search import parser

        return getattr(parser, name)
    raise AttributeError(f"module 'argupaper.agents' has no attribute {name!r}")
