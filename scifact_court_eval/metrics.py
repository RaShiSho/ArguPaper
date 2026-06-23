"""Metrics for SciFact court evaluation."""

from __future__ import annotations

from collections import Counter
from typing import Any

from scifact_court_eval.loaders import gold_chunk_ids
from scifact_court_eval.models import EvaluationRecord, EvaluationSummary, GoldLabel, JudgeScore, ScifactClaim

LABELS: tuple[GoldLabel, ...] = ("SUPPORT", "CONTRADICT", "NOT_ENOUGH_INFO")


def build_record(
    *,
    claim: ScifactClaim,
    court_report: dict[str, Any],
    judge: JudgeScore,
    baseline: dict[str, Any] | None,
) -> EvaluationRecord:
    """Build one scored evaluation record."""

    predicted_verdict = _first_verdict(court_report)
    predicted_label = verdict_to_label(predicted_verdict)
    retrieved_chunk_ids = _retrieved_chunk_ids(court_report)
    retrieved_doc_ids = [_doc_id_from_chunk_id(item) for item in retrieved_chunk_ids]
    retrieved_doc_ids = [item for item in retrieved_doc_ids if item is not None]
    retrieved_sentence_ids = [
        item for item in retrieved_chunk_ids if item.startswith("scifact:") and ":sent:" in item
    ]
    gold_ids = gold_chunk_ids(claim)
    gold_docs = {item.doc_id for item in claim.evidence_sets} or set(claim.cited_doc_ids)
    doc_hit = bool(gold_docs and set(retrieved_doc_ids) & gold_docs)
    sentence_hit = bool(set(retrieved_sentence_ids) & set(gold_ids))
    no_evidence_gold = claim.gold_label == "NOT_ENOUGH_INFO"
    no_evidence_abstained = no_evidence_gold and predicted_label == "NOT_ENOUGH_INFO"
    supported_hallucination = no_evidence_gold and predicted_label == "SUPPORT"

    return EvaluationRecord(
        claim_id=claim.claim_id,
        claim=claim.text,
        gold_label=claim.gold_label,
        cited_doc_ids=claim.cited_doc_ids,
        gold_evidence_chunk_ids=gold_ids,
        predicted_verdict=predicted_verdict,
        predicted_label=predicted_label,
        retrieved_chunk_ids=retrieved_chunk_ids,
        retrieved_doc_ids=list(dict.fromkeys(retrieved_doc_ids)),
        retrieved_sentence_ids=retrieved_sentence_ids,
        verdict_correct=predicted_label == claim.gold_label,
        doc_hit=doc_hit if claim.gold_label != "NOT_ENOUGH_INFO" else False,
        sentence_hit=sentence_hit if claim.gold_label != "NOT_ENOUGH_INFO" else False,
        no_evidence_abstained=no_evidence_abstained,
        supported_hallucination=supported_hallucination,
        judge=judge,
        court_report=court_report,
        baseline=baseline,
        warnings=[str(item) for item in court_report.get("warnings", [])],
    )


def summarize(records: list[EvaluationRecord]) -> EvaluationSummary:
    """Aggregate records into summary metrics."""

    total = len(records)
    if total == 0:
        return EvaluationSummary(
            total=0,
            verdict_accuracy=0.0,
            macro_f1=0.0,
            doc_recall_at_k=0.0,
            sentence_recall_at_k=0.0,
            no_evidence_abstention_rate=0.0,
            supported_hallucination_rate=0.0,
            judge_overall_score=0.0,
            hallucination_penalty_score=0.0,
            total_trust_score=0.0,
        )

    evidence_records = [item for item in records if item.gold_label != "NOT_ENOUGH_INFO"]
    no_evidence_records = [item for item in records if item.gold_label == "NOT_ENOUGH_INFO"]
    judge_success = [item.judge for item in records if not item.judge.failed]
    supported_hallucinations = sum(1 for item in records if item.supported_hallucination)
    supported_hallucination_rate = supported_hallucinations / max(1, len(no_evidence_records))
    judge_overall = (
        sum(item.overall_judge_score for item in judge_success) / len(judge_success)
        if judge_success
        else 0.0
    )
    hallucination_penalty_score = max(0.0, 1.0 - supported_hallucination_rate)
    verdict_accuracy = sum(1 for item in records if item.verdict_correct) / total
    evidence_recall = (
        sum(1 for item in evidence_records if item.sentence_hit) / len(evidence_records)
        if evidence_records
        else 0.0
    )
    total_trust_score = (
        0.40 * verdict_accuracy
        + 0.25 * evidence_recall
        + 0.20 * judge_overall
        + 0.15 * hallucination_penalty_score
    )

    return EvaluationSummary(
        total=total,
        verdict_accuracy=verdict_accuracy,
        macro_f1=_macro_f1(records),
        doc_recall_at_k=(
            sum(1 for item in evidence_records if item.doc_hit) / len(evidence_records)
            if evidence_records
            else 0.0
        ),
        sentence_recall_at_k=evidence_recall,
        no_evidence_abstention_rate=(
            sum(1 for item in no_evidence_records if item.no_evidence_abstained)
            / len(no_evidence_records)
            if no_evidence_records
            else 0.0
        ),
        supported_hallucination_rate=supported_hallucination_rate,
        judge_overall_score=judge_overall,
        hallucination_penalty_score=hallucination_penalty_score,
        total_trust_score=total_trust_score,
        label_counts=dict(Counter(item.gold_label for item in records)),
        predicted_label_counts=dict(Counter(item.predicted_label for item in records)),
        judge_failed_count=sum(1 for item in records if item.judge.failed),
    )


def verdict_to_label(verdict: str) -> GoldLabel:
    """Map court verdict into SciFact labels."""

    normalized = verdict.strip().lower()
    if normalized in {"supported", "weakly_supported"}:
        return "SUPPORT"
    if normalized in {"unsupported", "overclaimed"}:
        return "CONTRADICT"
    return "NOT_ENOUGH_INFO"


def _first_verdict(court_report: dict[str, Any]) -> str:
    verdicts = court_report.get("verdicts") or []
    if not verdicts:
        return "needs_external_validation"
    first = verdicts[0]
    if isinstance(first, dict):
        return str(first.get("verdict") or "needs_external_validation")
    return "needs_external_validation"


def _retrieved_chunk_ids(court_report: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in court_report.get("evidence", []) or []:
        if isinstance(item, dict):
            chunk_id = str(item.get("chunk_id", "")).strip()
            if chunk_id:
                ids.append(chunk_id)
    return list(dict.fromkeys(ids))


def _doc_id_from_chunk_id(chunk_id: str) -> int | None:
    parts = chunk_id.split(":")
    if len(parts) >= 4 and parts[0] == "scifact" and parts[2] == "sent":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def _macro_f1(records: list[EvaluationRecord]) -> float:
    f1_scores: list[float] = []
    for label in LABELS:
        true_positive = sum(
            1 for item in records if item.gold_label == label and item.predicted_label == label
        )
        false_positive = sum(
            1 for item in records if item.gold_label != label and item.predicted_label == label
        )
        false_negative = sum(
            1 for item in records if item.gold_label == label and item.predicted_label != label
        )
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        if precision + recall == 0:
            f1_scores.append(0.0)
        else:
            f1_scores.append(2 * precision * recall / (precision + recall))
    return sum(f1_scores) / len(f1_scores)

