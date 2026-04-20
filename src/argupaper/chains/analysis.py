"""Analysis chain for method principle breakdown."""

from langchain.callbacks import CallbackManagerForChainRun


class AnalysisChain:
    """Chain for systematic knowledge summary and technical analysis."""

    async def run(self, paper_markdown: str) -> dict:
        """Run analysis on paper markdown."""
        raise NotImplementedError("To be implemented")