"""Evidence chain for experiment information extraction."""

from langchain.callbacks import CallbackManagerForChainRun


class EvidenceChain:
    """Chain for extracting experiment details and evidence."""

    async def run(self, paper_markdown: str) -> dict:
        """Run evidence extraction on paper markdown."""
        raise NotImplementedError("To be implemented")