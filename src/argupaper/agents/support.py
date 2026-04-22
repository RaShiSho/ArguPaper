"""Support agent - defends the paper's claims."""

from argupaper.agents.base import AgentBase, AgentConfig


class SupportAgent(AgentBase):
    """Agent that provides supporting arguments for the paper."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def think(self, context: dict) -> str:
        """Generate supporting arguments."""

        round_number = int(context.get("round", 1))
        analysis = context.get("analysis", {})
        evidence = context.get("evidence", {})
        latest_skeptic_message = context.get("latest_skeptic_message", "").strip()
        supplementary_results = context.get("supplementary_results", [])

        overview = analysis.get("overview") or "the paper addresses a concrete research problem"
        technical_route = (
            analysis.get("technical_route")
            or analysis.get("method_analysis")
            or "a clearly scoped method"
        )
        datasets = [str(item) for item in evidence.get("datasets", []) if item]
        metrics = [str(item) for item in evidence.get("metrics", []) if item]
        claims = [str(item) for item in analysis.get("key_claims", []) if item]

        strengths: list[str] = []
        if evidence.get("has_baseline"):
            strengths.append("it includes an explicit baseline comparison")
        if evidence.get("has_ablation"):
            strengths.append("it reports an ablation or component-level check")
        if datasets:
            strengths.append(f"it evaluates on {', '.join(datasets[:3])}")
        if metrics:
            strengths.append(f"it reports {', '.join(metrics[:3])}")
        if supplementary_results:
            related_titles = [
                item.get("title", "related work")
                for item in supplementary_results[:2]
                if item.get("title")
            ]
            if related_titles:
                strengths.append(
                    f"its positioning can be checked against {', '.join(related_titles)}"
                )

        prefix = "Initial support position:" if round_number == 1 else "Support rebuttal:"
        rebuttal = ""
        if latest_skeptic_message:
            rebuttal = (
                " The skeptic raises evidence sufficiency concerns, but those concerns do not "
                "erase the concrete signal already present in the paper."
            )

        strengths_text = " ".join(strengths) if strengths else "it still provides some direct evidence"
        claims_text = ""
        if claims:
            claims_text = f" The main claim under defense is: {claims[0]}."

        return (
            f"{prefix} The paper is defensible because {overview}. "
            f"Its core technical route is {technical_route}, and {strengths_text}.{claims_text}"
            f"{rebuttal}"
        )
