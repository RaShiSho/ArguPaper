"""Markdown report rendering for SciFact court evaluation."""

from __future__ import annotations

from pathlib import Path

from scifact_court_eval.models import EvaluationRecord, EvaluationSummary


def write_reports(
    output_dir: Path,
    *,
    records: list[EvaluationRecord],
    summary: EvaluationSummary,
) -> None:
    """Write summary and failure Markdown reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.md").write_text(render_summary(summary), encoding="utf-8")
    (output_dir / "failures.md").write_text(render_failures(records), encoding="utf-8")


def render_summary(summary: EvaluationSummary) -> str:
    """Render aggregate metrics as Markdown."""

    lines = [
        "# SciFact Court Evaluation Summary",
        "",
        f"- Records: {summary.total}",
        f"- Verdict accuracy: {_pct(summary.verdict_accuracy)}",
        f"- Macro F1: {_pct(summary.macro_f1)}",
        f"- Doc recall@k: {_pct(summary.doc_recall_at_k)}",
        f"- Sentence recall@k: {_pct(summary.sentence_recall_at_k)}",
        f"- No-evidence abstention rate: {_pct(summary.no_evidence_abstention_rate)}",
        f"- Supported hallucination rate: {_pct(summary.supported_hallucination_rate)}",
        f"- Judge overall score: {_pct(summary.judge_overall_score)}",
        f"- Hallucination penalty score: {_pct(summary.hallucination_penalty_score)}",
        f"- Total trust score: {_pct(summary.total_trust_score)}",
        "",
        "## Weighting",
        "",
        "- 40% verdict accuracy",
        "- 25% evidence recall",
        "- 20% judge overall score",
        "- 15% hallucination penalty score",
        "",
        "## Label Counts",
        "",
        "| Label | Gold | Predicted |",
        "| --- | ---: | ---: |",
    ]
    for label in ("SUPPORT", "CONTRADICT", "NOT_ENOUGH_INFO"):
        lines.append(
            f"| {label} | {summary.label_counts.get(label, 0)} | "
            f"{summary.predicted_label_counts.get(label, 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_failures(records: list[EvaluationRecord]) -> str:
    """Render claim-level failures and high-risk cases."""

    failures = [
        record
        for record in records
        if (
            record.gold_label != record.predicted_label
            or record.supported_hallucination
            or record.judge.failed
        )
    ]
    lines = [
        "# SciFact Court Evaluation Failures",
        "",
        f"- Failure or warning cases: {len(failures)}",
        "",
    ]
    if not failures:
        lines.append("No failure cases recorded.")
        lines.append("")
        return "\n".join(lines)

    for record in failures:
        lines.extend(
            [
                f"## Claim {record.claim_id}",
                "",
                f"- Gold: {record.gold_label}",
                f"- Predicted: {record.predicted_label}",
                f"- Doc hit: {record.doc_hit}",
                f"- Sentence hit: {record.sentence_hit}",
                f"- Supported hallucination: {record.supported_hallucination}",
                f"- Judge failed: {record.judge.failed}",
            ]
        )
        if record.judge.error:
            lines.append(f"- Judge error: {record.judge.error}")
        if record.judge.rationale:
            lines.append(f"- Judge rationale: {record.judge.rationale}")
        lines.append("")
        if record.retrieved_chunk_ids:
            lines.append("Retrieved chunks:")
            for chunk_id in record.retrieved_chunk_ids[:10]:
                lines.append(f"- `{chunk_id}`")
            lines.append("")
    return "\n".join(lines)


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"
