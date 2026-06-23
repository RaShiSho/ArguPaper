"""Data models for SciFact court evaluation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GoldLabel = Literal["SUPPORT", "CONTRADICT", "NOT_ENOUGH_INFO"]


class ScifactDocument(BaseModel):
    """One SciFact corpus document."""

    doc_id: int
    title: str
    abstract: list[str] = Field(default_factory=list)
    structured: bool = False


class GoldEvidenceSet(BaseModel):
    """One SciFact gold evidence set for a claim."""

    doc_id: int
    sentences: list[int] = Field(default_factory=list)
    label: GoldLabel


class ScifactClaim(BaseModel):
    """One SciFact claim record."""

    claim_id: int
    text: str
    split: str
    cited_doc_ids: list[int] = Field(default_factory=list)
    evidence_sets: list[GoldEvidenceSet] = Field(default_factory=list)

    @property
    def gold_label(self) -> GoldLabel:
        """Return the claim-level label derived from gold evidence."""

        labels = {item.label for item in self.evidence_sets}
        if not labels:
            return "NOT_ENOUGH_INFO"
        if labels == {"SUPPORT"}:
            return "SUPPORT"
        if labels == {"CONTRADICT"}:
            return "CONTRADICT"
        return "NOT_ENOUGH_INFO"


class ScifactChunkRecord(BaseModel):
    """One SciFact sentence chunk ready for vector indexing."""

    chunk_id: str
    doc_id: int
    sentence_idx: int
    title: str
    text: str
    gold_split: str


class JudgeScore(BaseModel):
    """Structured Judge LLM score for one court result."""

    verdict_correctness: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_faithfulness: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_alignment: float = Field(default=0.0, ge=0.0, le=1.0)
    conservativeness: float = Field(default=0.0, ge=0.0, le=1.0)
    challenge_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_risk: float = Field(default=1.0, ge=0.0, le=1.0)
    overall_judge_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""
    failed: bool = False
    error: str | None = None


class EvaluationRecord(BaseModel):
    """One complete evaluated SciFact claim."""

    claim_id: int
    claim: str
    gold_label: GoldLabel
    cited_doc_ids: list[int] = Field(default_factory=list)
    gold_evidence_chunk_ids: list[str] = Field(default_factory=list)
    predicted_verdict: str
    predicted_label: GoldLabel
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    retrieved_doc_ids: list[int] = Field(default_factory=list)
    retrieved_sentence_ids: list[str] = Field(default_factory=list)
    verdict_correct: bool
    doc_hit: bool
    sentence_hit: bool
    no_evidence_abstained: bool
    supported_hallucination: bool
    judge: JudgeScore
    court_report: dict[str, Any]
    baseline: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    """Aggregate metrics for one SciFact evaluation run."""

    total: int
    verdict_accuracy: float
    macro_f1: float
    doc_recall_at_k: float
    sentence_recall_at_k: float
    no_evidence_abstention_rate: float
    supported_hallucination_rate: float
    judge_overall_score: float
    hallucination_penalty_score: float
    total_trust_score: float
    label_counts: dict[str, int] = Field(default_factory=dict)
    predicted_label_counts: dict[str, int] = Field(default_factory=dict)
    judge_failed_count: int = 0
