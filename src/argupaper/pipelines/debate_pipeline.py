"""Debate chain for multi-round adversarial discussion."""

from argupaper.agents.runtime.base import AgentBase, AgentConfig
from argupaper.agents.models import AgentMessage, DebateState
from argupaper.agents.roles.skeptic import SkepticAgent
from argupaper.agents.roles.support import SupportAgent
from argupaper.services.llm import LLMRouter


class DebateChain:
    """Chain for multi-agent debate with configurable rounds."""

    def __init__(self, max_rounds: int = 3, llm_router: LLMRouter | None = None):
        self.max_rounds = max(1, max_rounds)
        self.llm_router = llm_router
        self.support_agent = SupportAgent(
            AgentConfig(name="support", role="support"),
            llm_router=llm_router,
        )
        self.skeptic_agent = SkepticAgent(
            AgentConfig(name="skeptic", role="skeptic"),
            llm_router=llm_router,
        )

    async def run(self, initial_context: dict) -> DebateState:
        """Run multi-round debate."""

        self.support_agent.clear_history()
        self.skeptic_agent.clear_history()
        state = DebateState(
            current_claims=self._extract_claims(initial_context)
        )
        evidence_refs = self._collect_evidence_refs(initial_context)

        for round_number in range(1, self.max_rounds + 1):
            support_content, support_warnings = await self._safe_agent_think(
                self.support_agent,
                "support",
                {
                    **initial_context,
                    "round": round_number,
                    "latest_skeptic_message": (
                        state.skeptic_positions[-1] if state.skeptic_positions else ""
                    ),
                },
            )
            self._extend_warnings(state, support_warnings)
            self.support_agent.add_message("assistant", support_content)

            support_message = AgentMessage(
                agent_role="support",
                round=round_number,
                content=support_content,
                evidence_refs=evidence_refs,
                claims_refs=state.current_claims,
            )
            state.messages.append(support_message)
            state.support_positions.append(support_content)

            skeptic_content, skeptic_warnings = await self._safe_agent_think(
                self.skeptic_agent,
                "skeptic",
                {
                    **initial_context,
                    "round": round_number,
                    "latest_support_message": support_content,
                },
            )
            self._extend_warnings(state, skeptic_warnings)
            self.skeptic_agent.add_message("assistant", skeptic_content)

            skeptic_message = AgentMessage(
                agent_role="skeptic",
                round=round_number,
                content=skeptic_content,
                claims_refs=state.current_claims,
                evidence_refs=evidence_refs,
            )
            state.messages.append(skeptic_message)
            state.skeptic_positions.append(skeptic_content)
            state.round = round_number

            if await self.should_stop_early(state, initial_context):
                state.consensus_reached = True
                break

        return state

    async def _safe_agent_think(self, agent: AgentBase, role: str, context: dict) -> tuple[str, list[str]]:
        """Run one debate role and convert bad output into a reportable fallback."""

        try:
            content = (await agent.think(context)).strip()
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            warnings = agent.consume_warnings()
            warnings.append(f"{role} debate agent failed; used fallback: {reason}")
            return self._fallback_agent_content(role, reason), warnings

        warnings = agent.consume_warnings()
        if content:
            return content, warnings
        warnings.append(f"{role} debate agent returned empty output; used fallback.")
        return self._fallback_agent_content(role, "empty response"), warnings

    def _extend_warnings(self, state: DebateState, warnings: list[str]) -> None:
        for warning in warnings:
            if warning and warning not in state.warnings:
                state.warnings.append(warning)

    def _fallback_agent_content(self, role: str, reason: str) -> str:
        if role == "support":
            return (
                "Support fallback: this role produced no usable argument, so the positive case "
                f"must rely only on extracted analysis and evidence signals ({reason})."
            )
        if role == "skeptic":
            return (
                "Skeptic fallback: this role produced no usable critique, so unresolved evidence "
                f"risk should still be reviewed manually ({reason})."
            )
        return f"{role.title()} fallback: no usable debate output was produced ({reason})."

    async def should_stop_early(self, state: DebateState, initial_context: dict) -> bool:
        """Check if debate should stop before max rounds."""

        if state.round < 2:
            return False

        latest_skeptic = state.skeptic_positions[-1].lower() if state.skeptic_positions else ""
        if "no major blocking gap remains" in latest_skeptic:
            return True

        return not self._has_open_issues(initial_context)

    def _extract_claims(self, initial_context: dict) -> list[str]:
        analysis = initial_context.get("analysis", {})
        structured = initial_context.get("structured", {})
        claims = analysis.get("key_claims") or structured.get("claims") or []
        normalized_claims = [str(item).strip() for item in claims if str(item).strip()]
        if normalized_claims:
            return normalized_claims

        fallback_fields = [
            analysis.get("overview"),
            analysis.get("research_problem"),
            structured.get("problem"),
        ]
        return [str(item).strip() for item in fallback_fields if isinstance(item, str) and item.strip()]

    def _collect_evidence_refs(self, initial_context: dict) -> list[str]:
        evidence = initial_context.get("evidence", {})
        refs = [
            *[str(item) for item in evidence.get("datasets", []) if item],
            *[str(item) for item in evidence.get("metrics", []) if item],
        ]
        return list(dict.fromkeys(refs))

    def _has_open_issues(self, initial_context: dict) -> bool:
        evidence = initial_context.get("evidence", {})
        return any(
            [
                not evidence.get("has_baseline"),
                not evidence.get("has_ablation"),
                not evidence.get("metrics"),
                bool(evidence.get("unsupported_claims")),
                bool(evidence.get("contradictions")),
            ]
        )
