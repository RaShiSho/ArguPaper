"""Evidence chain for experiment information extraction."""

import re

from argupaper.extraction.claim_checker import ClaimChecker
from argupaper.extraction.structured import StructuredExtractor


class EvidenceChain:
    """Chain for extracting experiment details and evidence."""

    CLAIM_MARKERS = (
        "we propose",
        "we present",
        "we introduce",
        "we show",
        "we demonstrate",
        "our method",
        "outperform",
        "state-of-the-art",
        "improve",
        "effective",
        "robust",
        "novel",
    )

    def __init__(self) -> None:
        self.extractor = StructuredExtractor()
        self.claim_checker = ClaimChecker()

    async def run(self, paper_markdown: str) -> dict:
        """Run evidence extraction on paper markdown."""

        experiments = await self.extractor.extract_experiments(paper_markdown)
        experiment_text = self.extractor._extract_section(
            paper_markdown,
            ["experiment", "evaluation", "results"],
        )
        evidence_table = self._build_evidence_table(experiments)
        claims = self._extract_claims(paper_markdown)
        checker_evidence = [
            *evidence_table,
            {
                "dataset": ", ".join(experiments["datasets"]),
                "metric": ", ".join(experiments["metrics"]),
                "evidence": experiment_text,
                "support": experiment_text or "No experiment section detected.",
            },
        ]
        alignment = await self.claim_checker.check_alignment(claims, checker_evidence)
        sufficiency = await self.claim_checker.check_sufficiency(checker_evidence)

        has_baseline = experiments["has_baseline"] or sufficiency["has_baseline"]
        has_ablation = experiments["has_ablation"] or sufficiency["has_ablation"]

        weaknesses: list[str] = []
        if not experiments["datasets"]:
            weaknesses.append("No common benchmark dataset was confidently identified.")
        if not experiments["metrics"]:
            weaknesses.append("No standard evaluation metric was confidently identified.")
        if not has_baseline:
            weaknesses.append("Baseline comparison was not clearly detected.")
        if not has_ablation:
            weaknesses.append("Ablation analysis was not clearly detected.")
        if alignment["unsupported_claims"]:
            weaknesses.append(
                f"{len(alignment['unsupported_claims'])} claim(s) lack direct evidence alignment."
            )
        if alignment["contradictions"]:
            weaknesses.append(
                f"{len(alignment['contradictions'])} possible claim-evidence contradiction(s) detected."
            )

        return {
            "evidence_table": evidence_table,
            "claims": claims,
            "aligned_claims": alignment["aligned_claims"],
            "unsupported_claims": alignment["unsupported_claims"],
            "datasets": experiments["datasets"],
            "metrics": experiments["metrics"],
            "sample_sizes": experiments["sample_sizes"],
            "has_baseline": has_baseline,
            "has_ablation": has_ablation,
            "missing_analyses": sufficiency["missing_analyses"],
            "weakness_analysis": " ".join(weaknesses) if weaknesses else "Evidence coverage looks reasonable.",
            "contradictions": alignment["contradictions"],
            "needs_supplementary_search": (
                not has_baseline
                or bool(alignment["unsupported_claims"])
                or bool(alignment["contradictions"])
            ),
        }

    def _build_evidence_table(self, experiments: dict) -> list[dict[str, str]]:
        metrics = ", ".join(experiments["metrics"]) or "Not specified"
        datasets = experiments["datasets"]
        snippets = experiments.get("support_snippets", [])
        if datasets:
            return [
                {
                    "dataset": dataset,
                    "metric": metrics,
                    "support": self._select_support_snippet(dataset, experiments["metrics"], snippets),
                }
                for dataset in datasets
            ][:8]
        if experiments["metrics"]:
            return [
                {
                    "dataset": "Not specified",
                    "metric": metrics,
                    "support": (
                        snippets[0]
                        if snippets
                        else "Metrics were detected, but datasets were not clearly identified."
                    ),
                }
            ]
        return []

    def _select_support_snippet(
        self,
        dataset: str,
        metrics: list[str],
        snippets: list[str],
    ) -> str:
        dataset_lowered = dataset.casefold()
        for snippet in snippets:
            lowered = snippet.casefold()
            if dataset_lowered in lowered and any(metric.casefold() in lowered for metric in metrics):
                return snippet
        for snippet in snippets:
            if dataset_lowered in snippet.casefold():
                return snippet
        return "Referenced in experiment or evaluation section."

    def _extract_claims(self, paper_markdown: str) -> list[dict[str, str]]:
        focused_text = "\n".join(
            section
            for section in [
                self.extractor._extract_section(paper_markdown, ["abstract"]),
                self.extractor._extract_section(paper_markdown, ["introduction", "overview"]),
                self.extractor._extract_section(paper_markdown, ["conclusion", "discussion"]),
            ]
            if section
        )
        haystack = focused_text or paper_markdown[:5000]
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", haystack))
            if sentence.strip()
        ]

        claims: list[dict[str, str]] = []
        for sentence in sentences:
            lowered = sentence.casefold()
            if not any(marker in lowered for marker in self.CLAIM_MARKERS):
                continue
            if len(sentence) < 24:
                continue
            claims.append({"claim": self._truncate(sentence, 260)})
            if len(claims) >= 5:
                break

        if claims:
            return claims

        for sentence in sentences:
            if len(sentence) >= 24:
                return [{"claim": self._truncate(sentence, 260)}]
        return []

    def _truncate(self, text: str, limit: int) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."
