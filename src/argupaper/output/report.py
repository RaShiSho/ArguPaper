"""Report generation from analysis results."""

from argupaper.output.structures import ResearchReport


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

        method_comparison = "No supplementary comparison papers were retrieved."
        if supplementary_results:
            comparison_lines = [
                f"- {item.get('title', 'Untitled')} ({item.get('source', 'unknown')})"
                for item in supplementary_results
            ]
            method_comparison = "\n".join(comparison_lines)

        debate_summary = "No debate output available."
        if debate and debate.messages:
            last_support = next(
                (msg.content for msg in reversed(debate.messages) if msg.agent_role == "support"),
                "",
            )
            last_skeptic = next(
                (msg.content for msg in reversed(debate.messages) if msg.agent_role == "skeptic"),
                "",
            )
            debate_summary = f"Support: {last_support}\n\nSkeptic: {last_skeptic}"

        return ResearchReport(
            overview=analysis.get("overview") or structured.get("problem") or "No overview available.",
            method_comparison=method_comparison,
            evidence_table=evidence.get("evidence_table", []),
            debate_summary=debate_summary,
            contradictions=evidence.get("contradictions", []),
            weakness_analysis=evidence.get("weakness_analysis", "No weakness analysis available."),
            consensus_vs_disagreement={
                "consensus": consensus.get("consensus", []),
                "disagreement": consensus.get("disagreements", []),
                "supporting_evidence": consensus.get("supporting_evidence", []),
            },
            confidence_score=analysis_result.get("confidence_score", 50.0),
            conflict_intensity=analysis_result.get("conflict_intensity", "medium"),
        )

    def format_markdown(self, report: ResearchReport) -> str:
        """Format report as markdown string."""

        evidence_lines = ["| Dataset | Metric | Support |", "| --- | --- | --- |"]
        if report.evidence_table:
            for item in report.evidence_table:
                evidence_lines.append(
                    f"| {item.get('dataset', 'N/A')} | {item.get('metric', 'N/A')} | {item.get('support', 'N/A')} |"
                )
        else:
            evidence_lines.append("| N/A | N/A | No structured evidence extracted |")

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

## Method Comparison

{report.method_comparison}

## Evidence Table

{chr(10).join(evidence_lines)}

## Debate Summary

{report.debate_summary}

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
