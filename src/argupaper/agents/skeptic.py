"""Skeptic agent - challenges the paper's claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class SkepticAgent(AgentBase):
    """Agent that critically examines the paper."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate critical analysis."""
        raise NotImplementedError("To be implemented")