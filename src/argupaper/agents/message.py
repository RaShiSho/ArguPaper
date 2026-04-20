"""Data structures for agent messages and debate state."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import Literal


class AgentMessage(BaseModel):
    """Message from an agent in the debate."""
    agent_role: Literal[
        "support", "skeptic", "comparator", "evidence",
        "analysis", "critique", "judge"
    ]
    round: int
    content: str
    evidence_refs: list[str] = []
    claims_refs: list[str] = []
    timestamp: datetime = datetime.now()


class DebateState(BaseModel):
    """State of the multi-round debate."""
    round: int = 0
    messages: list[AgentMessage] = []
    current_claims: list[str] = []
    consensus_reached: bool = False
    support_positions: list[str] = []
    skeptic_positions: list[str] = []