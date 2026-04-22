"""Data structures for agent messages and debate state."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """Message from an agent in the debate."""

    agent_role: Literal[
        "support", "skeptic", "comparator", "evidence",
        "analysis", "critique", "judge"
    ]
    round: int
    content: str
    evidence_refs: list[str] = Field(default_factory=list)
    claims_refs: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class DebateState(BaseModel):
    """State of the multi-round debate."""

    round: int = 0
    messages: list[AgentMessage] = Field(default_factory=list)
    current_claims: list[str] = Field(default_factory=list)
    consensus_reached: bool = False
    support_positions: list[str] = Field(default_factory=list)
    skeptic_positions: list[str] = Field(default_factory=list)
