"""Support agent - defends the paper's claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class SupportAgent(AgentBase):
    """Agent that provides supporting arguments for the paper."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate supporting arguments."""
        raise NotImplementedError("To be implemented")