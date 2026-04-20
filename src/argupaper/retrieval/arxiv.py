"""ArXiv API client for paper retrieval."""

from typing import Optional


class ArXivClient:
    """Client for ArXiv API."""

    def __init__(self):
        pass

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search papers by query."""
        raise NotImplementedError("To be implemented")

    async def download_pdf(self, paper_id: str, save_path: str) -> str:
        """Download paper PDF to local path."""
        raise NotImplementedError("To be implemented")