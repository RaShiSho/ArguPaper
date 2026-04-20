"""Agent definitions for multi-agent debate system."""

from argupaper.agents.base import AgentBase
from argupaper.agents.support import SupportAgent
from argupaper.agents.skeptic import SkepticAgent
from argupaper.agents.comparator import ComparatorAgent
from argupaper.agents.evidence import EvidenceAgent

__all__ = [
    "AgentBase",
    "SupportAgent",
    "SkepticAgent",
    "ComparatorAgent",
    "EvidenceAgent",
]