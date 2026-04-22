"""Skeptic agent - challenges the paper's claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class SkepticAgent(AgentBase):
    """Agent that critically examines the paper."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate critical analysis."""

        evidence = context.get("evidence", {})
        weaknesses = []
        if not evidence.get("has_baseline"):
            weaknesses.append("baseline comparisons are unclear")
        if not evidence.get("has_ablation"):
            weaknesses.append("ablation evidence is missing or unclear")
        if not evidence.get("metrics"):
            weaknesses.append("evaluation metrics are not clearly stated")
        weakness_text = ", ".join(weaknesses) or "the empirical evidence remains limited"
        return (
            "The paper still has review risk because "
            f"{weakness_text}. These gaps make it harder to verify whether the main claims are "
            "fully supported rather than directionally plausible."
        )
