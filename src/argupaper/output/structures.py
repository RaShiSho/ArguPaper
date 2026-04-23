"""Research report output structures."""

from typing import Literal

from pydantic import BaseModel, Field


class MethodComparisonItem(BaseModel):
    """One supplementary comparison paper rendered in the report."""

    title: str
    source: str = "unknown"
    year: int | None = None
    citation_count: int = 0
    url: str = ""


class DebateRoundSummary(BaseModel):
    """Condensed view of one debate round."""

    round: int
    support: str = ""
    skeptic: str = ""


class DebateSummary(BaseModel):
    """Structured debate summary used by the report formatter."""

    rounds: list[DebateRoundSummary] = Field(default_factory=list)
    consensus_reached: bool = False


class ResearchReport(BaseModel):
    """Complete research analysis report."""

    overview: str
    method_comparison: list[MethodComparisonItem] = Field(default_factory=list)
    evidence_table: list[dict[str, str]] = Field(default_factory=list)
    debate_summary: DebateSummary = Field(default_factory=DebateSummary)
    contradictions: list[str] = Field(default_factory=list)
    weakness_analysis: str
    consensus_vs_disagreement: dict[str, list[str]] = Field(default_factory=dict)
    confidence_score: float
    conflict_intensity: Literal["low", "medium", "high"]
    warnings: list[str] = Field(default_factory=list)
