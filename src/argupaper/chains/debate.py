"""Debate chain for multi-round adversarial discussion."""

from argupaper.agents.base import AgentConfig
from argupaper.agents.message import AgentMessage, DebateState
from argupaper.agents.skeptic import SkepticAgent
from argupaper.agents.support import SupportAgent


class DebateChain:
    """Chain for multi-agent debate with configurable rounds."""

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds
        self.support_agent = SupportAgent(AgentConfig(name="support", role="support"))
        self.skeptic_agent = SkepticAgent(AgentConfig(name="skeptic", role="skeptic"))

    async def run(self, initial_context: dict) -> DebateState:
        """Run multi-round debate."""

        state = DebateState(
            current_claims=[initial_context.get("analysis", {}).get("overview", "")]
        )
        for round_number in range(1, self.max_rounds + 1):
            support_content = await self.support_agent.think(initial_context)
            skeptic_content = await self.skeptic_agent.think(initial_context)

            state.messages.append(
                AgentMessage(
                    agent_role="support",
                    round=round_number,
                    content=support_content,
                    evidence_refs=initial_context.get("evidence", {}).get("datasets", []),
                )
            )
            state.messages.append(
                AgentMessage(
                    agent_role="skeptic",
                    round=round_number,
                    content=skeptic_content,
                    claims_refs=state.current_claims,
                )
            )
            state.support_positions.append(support_content)
            state.skeptic_positions.append(skeptic_content)
            state.round = round_number

            if await self.should_stop_early(state):
                state.consensus_reached = True
                break

        return state

    async def should_stop_early(self, state: DebateState) -> bool:
        """Check if debate should stop before max rounds."""

        if state.round < 2:
            return False
        latest_skeptic = state.skeptic_positions[-1].lower() if state.skeptic_positions else ""
        return "missing" not in latest_skeptic and "unclear" not in latest_skeptic
