"""Research report output structures."""

from pydantic import BaseModel
from typing import Literal


class ResearchReport(BaseModel):
    """Complete research analysis report."""

    overview: str
    method_comparison: str
    evidence_table: list[dict]
    debate_summary: str
    contradictions: list[str]
    weakness_analysis: str
    consensus_vs_disagreement: dict
    confidence_score: float
    conflict_intensity: Literal["low", "medium", "high"]