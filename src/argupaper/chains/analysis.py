"""Analysis chain for method principle breakdown."""

from argupaper.extraction.structured import StructuredExtractor


class AnalysisChain:
    """Chain for systematic knowledge summary and technical analysis."""

    def __init__(self):
        self.extractor = StructuredExtractor()

    async def run(self, paper_markdown: str) -> dict:
        """Run analysis on paper markdown."""

        abstract = await self.extractor.extract_abstract(paper_markdown)
        method = await self.extractor.extract_method(paper_markdown)
        title = self._extract_title(paper_markdown)

        weaknesses = []
        if not method.get("limitations"):
            weaknesses.append("Limitations are not explicitly stated in the paper text.")

        return {
            "title": title,
            "overview": abstract["problem"] or "The paper presents a research contribution.",
            "research_problem": abstract["problem"],
            "method_analysis": method["details"] or abstract["method"],
            "technical_route": abstract["method"],
            "weakness_hints": weaknesses,
        }

    def _extract_title(self, markdown: str) -> str:
        for line in markdown.splitlines()[:20]:
            if line.startswith("# "):
                return line[2:].strip()
        return "Research Paper Analysis"
