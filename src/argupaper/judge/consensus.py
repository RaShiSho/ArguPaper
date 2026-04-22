"""Consensus detection and confidence scoring."""

from typing import Literal


class ConsensusDetector:
    """Detects consensus and disagreements from debate results."""

    async def detect_consensus(self, debate_messages: list[dict]) -> dict:
        """Detect consensus points from debate."""

        support_messages = [msg for msg in debate_messages if msg.get("agent_role") == "support"]
        skeptic_messages = [msg for msg in debate_messages if msg.get("agent_role") == "skeptic"]

        consensus = []
        if support_messages:
            consensus.append("The paper addresses a meaningful research problem.")

        disagreements = []
        if skeptic_messages:
            disagreements.append(skeptic_messages[-1].get("content", "Evidence adequacy remains debated."))

        supporting_evidence: list[str] = []
        for message in support_messages:
            supporting_evidence.extend(message.get("evidence_refs", []))

        return {
            "consensus": consensus,
            "disagreements": disagreements,
            "supporting_evidence": list(dict.fromkeys(supporting_evidence)),
        }

    async def compute_confidence(
        self,
        support_score: float,
        oppose_score: float,
    ) -> tuple[float, Literal["low", "medium", "high"]]:
        """Compute confidence score and conflict intensity."""

        total = max(support_score + oppose_score, 1.0)
        confidence = max(0.0, min(100.0, (support_score / total) * 100.0))
        disagreement_ratio = abs(support_score - oppose_score) / total
        if disagreement_ratio < 0.2:
            intensity: Literal["low", "medium", "high"] = "high"
        elif disagreement_ratio < 0.5:
            intensity = "medium"
        else:
            intensity = "low"
        return round(confidence, 2), intensity
