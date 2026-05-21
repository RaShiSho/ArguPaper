"""Skeptic agent - challenges the paper's claims."""

from langchain_core.prompts import ChatPromptTemplate

from argupaper.agents.base import AgentBase, AgentConfig
from argupaper.llm import LLMRouter, build_llm_router_runnable
from argupaper.prompts import load_prompt


SKEPTIC_SYSTEM_PROMPT = load_prompt("skeptic_agent", "system.md")
SKEPTIC_USER_PROMPT = load_prompt("skeptic_agent", "user.md")


class SkepticAgent(AgentBase):
    """Agent that critically examines the paper."""

    def __init__(self, config: AgentConfig, llm_router: LLMRouter | None = None):
        super().__init__(config)
        self.llm_router = llm_router
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SKEPTIC_SYSTEM_PROMPT),
                ("human", SKEPTIC_USER_PROMPT),
            ]
        )

    async def think(self, context: dict) -> str:
        """Generate critical analysis."""

        langchain_content = await self._think_with_langchain(context)
        if langchain_content:
            return langchain_content
        return self._fallback_think(context)

    async def _think_with_langchain(self, context: dict) -> str:
        if self.llm_router is None:
            self.add_warning("Skeptic LangChain role skipped; no LLM router was provided.")
            return ""
        if not self.llm_router.has_provider("default"):
            self.add_warning(
                "Skeptic LangChain role skipped; default LLM provider is not configured."
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
                "Skeptic LangChain role failed; used deterministic fallback: "
                f"{type(exc).__name__}: {exc}"
            )
            return ""
        if content:
            return content
        self.add_warning("Skeptic LangChain role returned empty output; used deterministic fallback.")
        return ""

    def _prompt_input(self, context: dict) -> dict[str, str | int]:
        return {
            "round_number": int(context.get("round", 1)),
            "analysis": self.format_context_value(context.get("analysis", {})),
            "evidence": self.format_context_value(context.get("evidence", {})),
            "structured": self.format_context_value(context.get("structured", {})),
            "latest_support_message": str(context.get("latest_support_message", "")).strip()
            or "None yet.",
            "supplementary_results": self.format_context_value(
                context.get("supplementary_results", []),
                limit=2000,
            ),
        }

    def _fallback_think(self, context: dict) -> str:
        """Generate deterministic skeptical analysis."""

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
