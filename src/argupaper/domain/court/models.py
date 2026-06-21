"""Structured models for claim-level adversarial paper review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal["method", "novelty", "experiment", "generalization", "causal"]
EvidenceKind = Literal["paper_chunk", "figure_caption", "table_caption", "external_paper"]
AttackTemplate = Literal[
    "novelty_attack",
    "baseline_attack",
    "dataset_attack",
    "metric_attack",
    "ablation_attack",
    "causal_attack",
    "generalization_attack",
    "reproducibility_attack",
]
ArgumentRole = Literal["challenge", "defense"]
VerdictLabel = Literal[
    "supported",
    "weakly_supported",
    "overclaimed",
    "unsupported",
    "needs_external_validation",
]
RiskLevel = Literal["low", "medium", "high", "critical"]


class Claim(BaseModel):
    """One paper claim under review."""

    claim_id: str
    text: str
    claim_type: ClaimType
    source: str = "paper"
    section: str = "unknown"
    page: int | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Evidence(BaseModel):
    """Evidence bound to a claim with stable citation metadata."""

    evidence_id: str
    claim_id: str
    kind: EvidenceKind
    text: str
    chunk_id: str
    source: str
    page: int | None = None
    section: str = "unknown"
    score: float = Field(default=0.0, ge=0.0)
    title: str | None = None
    url: str | None = None


class Argument(BaseModel):
    """A structured challenge or defense argument."""

    argument_id: str
    claim_id: str
    role: ArgumentRole
    content: str
    template: AttackTemplate | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    round: int = Field(default=1, ge=1)


class Dispute(BaseModel):
    """One challenge-defense pair for a claim."""

    dispute_id: str
    claim_id: str
    round: int = Field(default=1, ge=1)
    challenge: Argument
    defense: Argument | None = None
    unresolved_disputes: list[str] = Field(default_factory=list)
    resolved: bool = False


class ClaimVerdict(BaseModel):
    """Adjudicator decision for one claim."""

    claim_id: str
    verdict: VerdictLabel
    rationale: str
    risk_level: RiskLevel
    suggested_revision: str
    required_check: str
    converged: bool = False


class CriticalClaimReport(BaseModel):
    """Final structured output for Adversarial Paper Court."""

    paper_id: str
    title: str = "Untitled"
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    challenges: list[Argument] = Field(default_factory=list)
    defenses: list[Argument] = Field(default_factory=list)
    disputes: list[Dispute] = Field(default_factory=list)
    verdicts: list[ClaimVerdict] = Field(default_factory=list)
    max_rounds: int = 2
    rounds_completed: int = 0
    stop_reason: str = ""
    warnings: list[str] = Field(default_factory=list)

