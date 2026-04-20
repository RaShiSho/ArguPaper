"""Evidence agent - provides supporting evidence for claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class EvidenceAgent(AgentBase):
    """Agent that retrieves and provides evidence."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Retrieve and present evidence."""
        raise NotImplementedError("To be implemented")