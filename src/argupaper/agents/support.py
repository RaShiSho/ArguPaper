"""Support agent - defends the paper's claims."""

from langchain_core.prompts import ChatPromptTemplate

from argupaper.agents.base import AgentBase, AgentConfig
from argupaper.llm import LLMRouter, build_llm_router_runnable
from argupaper.prompts import load_prompt


SUPPORT_SYSTEM_PROMPT = load_prompt("support_agent", "system.md")
SUPPORT_USER_PROMPT = load_prompt("support_agent", "user.md")


class SupportAgent(AgentBase):
    """Agent that provides supporting arguments for the paper."""

    def __init__(self, config: AgentConfig, llm_router: LLMRouter | None = None):
        super().__init__(config)
        self.llm_router = llm_router
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SUPPORT_SYSTEM_PROMPT),
                ("human", SUPPORT_USER_PROMPT),
            ]
        )

    async def think(self, context: dict) -> str:
        """Generate supporting arguments."""

        langchain_content = await self._think_with_langchain(context)
        if langchain_content:
            return langchain_content
        return self._fallback_think(context)

    async def _think_with_langchain(self, context: dict) -> str:
        if self.llm_router is None:
            self.add_warning("Support LangChain role skipped; no LLM router was provided.")
            return ""
        if not self.llm_router.has_provider("default"):
            self.add_warning(
                "Support LangChain role skipped; default LLM provider is not configured."
            )
            return ""

        runnable = self.prompt | build_llm_router_runnable(
            self.llm_router,
            provider_alias="default",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        try:
            content = (await runnable.ainvoke(self._prompt_input(context))).strip()
        except Exception as exc:
            self.add_warning(
                "Support LangChain role failed; used deterministic fallback: "
                f"{type(exc).__name__}: {exc}"
            )
            return ""
        if content:
            return content
        self.add_warning("Support LangChain role returned empty output; used deterministic fallback.")
        return ""

    def _prompt_input(self, context: dict) -> dict[str, str | int]:
        return {
            "round_number": int(context.get("round", 1)),
            "analysis": self.format_context_value(context.get("analysis", {})),
            "evidence": self.format_context_value(context.get("evidence", {})),
            "structured": self.format_context_value(context.get("structured", {})),
            "latest_skeptic_message": str(context.get("latest_skeptic_message", "")).strip()
            or "None yet.",
            "supplementary_results": self.format_context_value(
                context.get("supplementary_results", []),
                limit=2000,
            ),
        }

    def _fallback_think(self, context: dict) -> str:
        """Generate deterministic supporting arguments."""

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
