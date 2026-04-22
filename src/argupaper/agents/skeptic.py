"""Skeptic agent - challenges the paper's claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class SkepticAgent(AgentBase):
    """Agent that critically examines the paper."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate critical analysis."""

        round_number = int(context.get("round", 1))
        latest_support_message = context.get("latest_support_message", "").strip()
        evidence = context.get("evidence", {})
        analysis = context.get("analysis", {})
        weaknesses = []

        if not evidence.get("has_baseline"):
            weaknesses.append("baseline comparisons remain unclear")
        if not evidence.get("has_ablation"):
            weaknesses.append("ablation evidence is missing or unclear")
        if not evidence.get("metrics"):
            weaknesses.append("evaluation metrics are not clearly stated")
        unsupported_claims = [str(item) for item in evidence.get("unsupported_claims", []) if item]
        contradictions = [str(item) for item in evidence.get("contradictions", []) if item]
        weakness_hints = [str(item) for item in analysis.get("weakness_hints", []) if item]

        if unsupported_claims:
            weaknesses.append(f"some claims still lack direct support: {unsupported_claims[0]}")
        if contradictions:
            weaknesses.append(f"reported evidence contains unresolved tension: {contradictions[0]}")
        if weakness_hints:
            weaknesses.append(weakness_hints[0])

        prefix = "Initial skeptic position:" if round_number == 1 else "Skeptic reply:"
        if not weaknesses:
            return (
                f"{prefix} The support case is mostly credible. No major blocking gap remains, "
                "although external validity and reproducibility still deserve review."
            )

        support_counter = ""
        if latest_support_message:
            support_counter = (
                " The support side highlights concrete positives, but those points do not fully "
                "resolve the remaining review risks."
            )

        weakness_text = "; ".join(weaknesses)
        return (
            f"{prefix} The paper still has review risk because {weakness_text}."
            f"{support_counter} These gaps make it harder to verify whether the main claims are "
            "fully supported rather than directionally plausible."
        )
