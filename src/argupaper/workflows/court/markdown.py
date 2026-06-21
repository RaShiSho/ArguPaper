"""Markdown rendering for CriticalClaimReport."""

from __future__ import annotations

from argupaper.domain.court import Claim, ClaimVerdict, CriticalClaimReport, Dispute, Evidence


def render_critical_claim_report(report: CriticalClaimReport) -> str:
    """Render the structured court report as Markdown."""

    lines = [
        f"# Critical Claim Report: {report.title}",
        "",
        f"- Paper ID: `{report.paper_id}`",
        f"- Rounds completed: {report.rounds_completed}/{report.max_rounds}",
        f"- Stop reason: {report.stop_reason or 'not specified'}",
        "",
    ]
    if report.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report.warnings)
        lines.append("")

    verdict_by_claim = {item.claim_id: item for item in report.verdicts}
    disputes_by_claim: dict[str, list[Dispute]] = {}
    evidence_by_claim: dict[str, list[Evidence]] = {}
    for dispute in report.disputes:
        disputes_by_claim.setdefault(dispute.claim_id, []).append(dispute)
    for evidence in report.evidence:
        evidence_by_claim.setdefault(evidence.claim_id, []).append(evidence)

    lines.extend(["## Claim Reviews", ""])
    for claim in report.claims:
        verdict = verdict_by_claim.get(claim.claim_id)
        claim_evidence = evidence_by_claim.get(claim.claim_id, [])
        claim_disputes = disputes_by_claim.get(claim.claim_id, [])
        lines.extend(_render_claim_review(claim, claim_evidence, claim_disputes, verdict))
        lines.append("")

    lines.extend(["## Structured Summary", ""])
    lines.append("| Claim | Verdict | Risk | Required Check |")
    lines.append("| --- | --- | --- | --- |")
    for claim in report.claims:
        verdict = verdict_by_claim.get(claim.claim_id)
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table(claim.claim_id),
                    _escape_table(verdict.verdict if verdict else "missing"),
                    _escape_table(verdict.risk_level if verdict else "unknown"),
                    _escape_table(verdict.required_check if verdict else "Manual review required."),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_claim_review(
    claim: Claim,
    evidence: list[Evidence],
    disputes: list[Dispute],
    verdict: ClaimVerdict | None,
) -> list[str]:
    lines = [
        f"### {claim.claim_id} [{claim.claim_type}]",
        "",
        f"**claim**: {claim.text}",
        "",
        "**evidence**:",
    ]
    if evidence:
        for item in evidence:
            page = "n/a" if item.page is None else str(item.page)
            title = f" `{item.title}`" if item.title else ""
            lines.append(
                f"- `{item.evidence_id}` {item.kind}{title}: "
                f"chunk_id=`{item.chunk_id}`, source=`{item.source}`, page={page}, "
                f"section=`{item.section}`, score={item.score}. {item.text}"
            )
    else:
        lines.append("- No bound evidence.")

    lines.extend(["", "**challenge / defense / unresolved_disputes**:"])
    if disputes:
        for dispute in disputes:
            lines.append(f"- Challenge ({dispute.challenge.template}, round {dispute.round}): {dispute.challenge.content}")
            if dispute.defense is not None:
                lines.append(f"  Defense: {dispute.defense.content}")
            if dispute.unresolved_disputes:
                for unresolved in dispute.unresolved_disputes:
                    lines.append(f"  Unresolved: {unresolved}")
            else:
                lines.append("  Unresolved: none")
    else:
        lines.append("- No disputes generated.")

    if verdict is None:
        lines.extend(
            [
                "",
                "**risk_level**: unknown",
                "**suggested_revision**: Manual review required.",
                "**required_check**: Manual review required.",
            ]
        )
        return lines

    lines.extend(
        [
            "",
            f"**verdict**: {verdict.verdict}",
            f"**risk_level**: {verdict.risk_level}",
            f"**suggested_revision**: {verdict.suggested_revision}",
            f"**required_check**: {verdict.required_check}",
            f"**rationale**: {verdict.rationale}",
        ]
    )
    return lines


def _escape_table(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")

