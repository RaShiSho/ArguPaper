"""Comparator agent - brings in competing methods/papers."""

from argupaper.agents.base import AgentBase, AgentConfig


class ComparatorAgent(AgentBase):
    """Agent that introduces comparison with other methods."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate comparative analysis."""
        raise NotImplementedError("To be implemented")