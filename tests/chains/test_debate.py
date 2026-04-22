"""Tests for the 2-agent debate workflow."""

import pytest

from argupaper.agents.message import DebateState
from argupaper.chains.debate import DebateChain


def _build_context(**evidence_overrides: object) -> dict:
    evidence = {
        "datasets": ["CIFAR-10"],
        "metrics": ["accuracy"],
        "has_baseline": True,
        "has_ablation": True,
        "unsupported_claims": [],
        "contradictions": [],
    }
    evidence.update(evidence_overrides)
    return {
        "analysis": {
            "overview": "the paper studies robust image classification",
            "technical_route": "a regularized contrastive training objective",
            "key_claims": ["the method improves robustness without large accuracy loss"],
            "weakness_hints": [],
        },
        "evidence": evidence,
    }


@pytest.mark.asyncio
async def test_debate_stops_early_when_evidence_is_complete() -> None:
    chain = DebateChain(max_rounds=4)

    state = await chain.run(_build_context())

    assert state.consensus_reached is True
    assert state.round == 2
    assert len(state.messages) == 4
    assert state.messages[0].agent_role == "support"
    assert state.messages[1].agent_role == "skeptic"
    assert "no major blocking gap remains" in state.skeptic_positions[-1].lower()


@pytest.mark.asyncio
async def test_debate_uses_full_round_budget_when_review_gaps_remain() -> None:
    chain = DebateChain(max_rounds=3)

    state = await chain.run(
        _build_context(
            has_baseline=False,
            has_ablation=False,
            metrics=[],
        )
    )

    assert state.consensus_reached is False
    assert state.round == 3
    assert len(state.messages) == 6
    assert "baseline comparisons remain unclear" in state.skeptic_positions[0].lower()
    assert state.messages[0].evidence_refs == ["CIFAR-10"]


def test_debate_state_defaults_are_not_shared_between_runs() -> None:
    first_state = DebateState()
    second_state = DebateState()

    first_state.current_claims.append("claim-a")
    first_state.support_positions.append("support")

    assert second_state.current_claims == []
    assert second_state.support_positions == []
