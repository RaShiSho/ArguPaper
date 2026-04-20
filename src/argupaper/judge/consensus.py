"""Consensus detection and confidence scoring."""

from typing import Literal, Optional


class ConsensusDetector:
    """Detects consensus and disagreements from debate results."""

    def __init__(self):
        pass

    async def detect_consensus(self, debate_messages: list[dict]) -> dict:
        """Detect consensus points from debate.

        Returns:
            dict with keys: consensus, disagreements, supporting_evidence
        """
        raise NotImplementedError("To be implemented")

    async def compute_confidence(
        self,
        support_score: float,
        oppose_score: float
    ) -> tuple[float, Literal["low", "medium", "high"]]:
        """Compute confidence score and conflict intensity.

        Returns:
            tuple of (confidence_score, conflict_intensity)
        """
        raise NotImplementedError("To be implemented")