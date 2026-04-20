"""Debate chain for multi-round adversarial discussion."""

from typing import Optional
from argupaper.agents.message import DebateState


class DebateChain:
    """Chain for multi-agent debate with configurable rounds."""

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds

    async def run(self, initial_context: dict) -> DebateState:
        """Run multi-round debate."""
        raise NotImplementedError("To be implemented")

    async def should_stop_early(self, state: DebateState) -> bool:
        """Check if debate should stop before max rounds."""
        raise NotImplementedError("To be implemented")