"""Evidence chain for experiment information extraction."""

from argupaper.extraction.structured import StructuredExtractor


class EvidenceChain:
    """Chain for extracting experiment details and evidence."""

    def __init__(self):
        self.extractor = StructuredExtractor()

    async def run(self, paper_markdown: str) -> dict:
        """Run evidence extraction on paper markdown."""

        experiments = await self.extractor.extract_experiments(paper_markdown)
        evidence_table = [
            {
                "dataset": dataset,
                "metric": ", ".join(experiments["metrics"]) or "Not specified",
                "support": "Referenced in evaluation section",
            }
            for dataset in experiments["datasets"]
        ]
        weaknesses: list[str] = []
        if not experiments["datasets"]:
            weaknesses.append("No common benchmark dataset was confidently identified.")
        if not experiments["metrics"]:
            weaknesses.append("No standard evaluation metric was confidently identified.")
        if not experiments["has_baseline"]:
            weaknesses.append("Baseline comparison was not clearly detected.")
        if not experiments["has_ablation"]:
            weaknesses.append("Ablation analysis was not clearly detected.")

        return {
            "evidence_table": evidence_table,
            "datasets": experiments["datasets"],
            "metrics": experiments["metrics"],
            "sample_sizes": experiments["sample_sizes"],
            "has_baseline": experiments["has_baseline"],
            "has_ablation": experiments["has_ablation"],
            "weakness_analysis": " ".join(weaknesses) if weaknesses else "Evidence coverage looks reasonable.",
            "contradictions": [],
            "needs_supplementary_search": not experiments["has_baseline"],
        }
