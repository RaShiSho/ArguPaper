"""Support agent - defends the paper's claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class SupportAgent(AgentBase):
    """Agent that provides supporting arguments for the paper."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate supporting arguments."""

        analysis = context.get("analysis", {})
        evidence = context.get("evidence", {})
        overview = analysis.get("overview", "The paper addresses an important problem.")
        datasets = ", ".join(evidence.get("datasets", [])[:3]) or "reported datasets"
        metrics = ", ".join(evidence.get("metrics", [])[:3]) or "reported metrics"
        return (
            f"The paper makes a credible case because it targets a concrete problem: {overview} "
            f"It also reports evaluation evidence on {datasets} with {metrics}, which provides "
            "at least some empirical support for the claimed contribution."
        )
