"""Report generation from analysis results."""

from argupaper.output.structures import (
    DebateRoundSummary,
    DebateSummary,
    MethodComparisonItem,
    ResearchReport,
)


class ReportGenerator:
    """Generates formatted research reports."""

    async def generate(self, analysis_result: dict) -> ResearchReport:
        """Generate research report from analysis results."""

        analysis = analysis_result.get("analysis", {})
        evidence = analysis_result.get("evidence", {})
        consensus = analysis_result.get("consensus", {})
        debate = analysis_result.get("debate")
        structured = analysis_result.get("structured", {})
        supplementary_results = analysis_result.get("supplementary_results", [])
        warnings = [str(item) for item in analysis_result.get("warnings", []) if str(item)]

        method_comparison = [
            MethodComparisonItem(
                title=str(item.get("title", "Untitled")),
                source=str(item.get("source", "unknown")),
                year=item.get("year"),
                citation_count=int(item.get("citation_count", 0) or 0),
                url=str(item.get("url", "")),
            )
            for item in supplementary_results
        ]

        weakness_parts: list[str] = []
        evidence_weakness = str(evidence.get("weakness_analysis", "")).strip()
        if evidence_weakness:
            weakness_parts.append(evidence_weakness)
        weakness_parts.extend(
            str(item).strip()
            for item in analysis.get("weakness_hints", [])
            if str(item).strip()
        )
        weakness_analysis = " ".join(dict.fromkeys(weakness_parts)) or "No weakness analysis available."

        return ResearchReport(
            overview=analysis.get("overview") or structured.get("problem") or "No overview available.",
            method_comparison=method_comparison,
            evidence_table=[
                {
                    "dataset": str(item.get("dataset", "N/A")),
                    "metric": str(item.get("metric", "N/A")),
                    "support": str(item.get("support", "N/A")),
                }
                for item in evidence.get("evidence_table", [])
            ],
            debate_summary=self._summarize_debate(debate),
            contradictions=[
                str(item).strip()
                for item in evidence.get("contradictions", [])
                if str(item).strip()
            ],
            weakness_analysis=weakness_analysis,
            consensus_vs_disagreement={
                "consensus": [
                    str(item).strip()
                    for item in consensus.get("consensus", [])
                    if str(item).strip()
                ],
                "disagreement": [
                    str(item).strip()
                    for item in consensus.get("disagreements", [])
                    if str(item).strip()
                ],
                "supporting_evidence": [
                    str(item).strip()
                    for item in consensus.get("supporting_evidence", [])
                    if str(item).strip()
                ],
            },
            confidence_score=float(analysis_result.get("confidence_score", 50.0)),
            conflict_intensity=analysis_result.get("conflict_intensity", "medium"),
            warnings=warnings,
        )

    def format_markdown(self, report: ResearchReport) -> str:
        """Format report as markdown string."""

        warning_lines = "\n".join(f"- {item}" for item in report.warnings) or "- None"

        method_comparison_lines: list[str] = []
        if report.method_comparison:
            for item in report.method_comparison:
                details: list[str] = [item.source]
                if item.year is not None:
                    details.append(str(item.year))
                details.append(f"citations: {item.citation_count}")
                detail_text = ", ".join(details)
                url_text = f" - {item.url}" if item.url else ""
                method_comparison_lines.append(f"- {item.title} ({detail_text}){url_text}")
        else:
            method_comparison_lines.append("- No supplementary comparison papers were retrieved.")

        evidence_lines = ["| Dataset | Metric | Support |", "| --- | --- | --- |"]
        if report.evidence_table:
            for item in report.evidence_table:
                evidence_lines.append(
                    f"| {item.get('dataset', 'N/A')} | {item.get('metric', 'N/A')} | {item.get('support', 'N/A')} |"
                )
        else:
            evidence_lines.append("| N/A | N/A | No structured evidence extracted |")

        debate_lines: list[str] = []
        if report.debate_summary.rounds:
            for round_summary in report.debate_summary.rounds:
                debate_lines.append(f"### Round {round_summary.round}")
                debate_lines.append(f"- Support: {round_summary.support or 'N/A'}")
                debate_lines.append(f"- Skeptic: {round_summary.skeptic or 'N/A'}")
            debate_lines.append("")
            debate_lines.append(
                f"- Early consensus reached: {'yes' if report.debate_summary.consensus_reached else 'no'}"
            )
        else:
            debate_lines.append("No debate output available.")

        contradictions = "\n".join(f"- {item}" for item in report.contradictions) or "- None detected"
        consensus = "\n".join(
            f"- {item}" for item in report.consensus_vs_disagreement.get("consensus", [])
        ) or "- None"
        disagreement = "\n".join(
            f"- {item}" for item in report.consensus_vs_disagreement.get("disagreement", [])
        ) or "- None"
        supporting_evidence = "\n".join(
            f"- {item}" for item in report.consensus_vs_disagreement.get("supporting_evidence", [])
        ) or "- None"

        return f"""# Research Overview

{report.overview}

## Warnings

{warning_lines}

## Method Comparison

{chr(10).join(method_comparison_lines)}

## Evidence Table

{chr(10).join(evidence_lines)}

## Debate Summary

{chr(10).join(debate_lines)}

## Contradictions

{contradictions}

## Weakness Analysis

{report.weakness_analysis}

## Consensus vs Disagreement

### Consensus

{consensus}

### Disagreement

{disagreement}

### Supporting Evidence

{supporting_evidence}

## Confidence Score

- Confidence: {report.confidence_score:.2f}
- Conflict intensity: {report.conflict_intensity}
"""

    def _summarize_debate(self, debate: object) -> DebateSummary:
        if debate is None or not hasattr(debate, "messages"):
            return DebateSummary()

        rounds: dict[int, dict[str, str]] = {}
        for message in getattr(debate, "messages", []):
            round_number = int(getattr(message, "round", 0) or 0)
            if round_number <= 0:
                continue
            entry = rounds.setdefault(round_number, {"support": "", "skeptic": ""})
            agent_role = str(getattr(message, "agent_role", "")).strip()
            if agent_role == "support":
                entry["support"] = str(getattr(message, "content", "")).strip()
            elif agent_role == "skeptic":
                entry["skeptic"] = str(getattr(message, "content", "")).strip()

        return DebateSummary(
            rounds=[
                DebateRoundSummary(
                    round=round_number,
                    support=payload["support"],
                    skeptic=payload["skeptic"],
                )
                for round_number, payload in sorted(rounds.items())
            ],
            consensus_reached=bool(getattr(debate, "consensus_reached", False)),
        )
