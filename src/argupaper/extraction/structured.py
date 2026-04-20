"""Structured extraction from paper markdown."""

from typing import Optional


class StructuredExtractor:
    """Extracts structured information from paper markdown."""

    def __init__(self):
        pass

    async def extract_abstract(self, markdown: str) -> dict:
        """Extract structured abstract (Problem/Method/Experiment/Conclusion)."""
        raise NotImplementedError("To be implemented")

    async def extract_experiments(self, markdown: str) -> dict:
        """Extract experiment information (datasets, metrics, sample sizes)."""
        raise NotImplementedError("To be implemented")

    async def extract_method(self, markdown: str) -> dict:
        """Extract method details (assumptions, scope, limitations)."""
        raise NotImplementedError("To be implemented")