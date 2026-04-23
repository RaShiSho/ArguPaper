"""Tests for consensus detection behavior."""

from __future__ import annotations

import pytest

from argupaper.judge.consensus import ConsensusDetector


@pytest.mark.asyncio
async def test_detect_consensus_excludes_positive_skeptic_conclusion_from_disagreements() -> None:
    detector = ConsensusDetector()

    result = await detector.detect_consensus(
        [
            {
                "agent_role": "support",
                "content": "The evidence covers the claimed gains.",
                "evidence_refs": ["CIFAR-10", "accuracy"],
            },
            {
                "agent_role": "skeptic",
                "content": "The support case is mostly credible. No major blocking gap remains.",
            },
        ],
        analysis={
            "research_problem": "robust image classification",
            "technical_route": "regularized contrastive training",
        },
        evidence={
            "datasets": ["CIFAR-10"],
            "metrics": ["accuracy"],
            "has_baseline": True,
            "has_ablation": True,
            "unsupported_claims": [],
            "contradictions": [],
        },
    )

    assert result["disagreements"] == []
