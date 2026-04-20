"""MinerU API client for PDF to Markdown conversion."""

import hashlib
from typing import Optional
from pathlib import Path


class MinerUClient:
    """Client for MinerU PDF conversion API."""

    def __init__(self, api_key: str, api_endpoint: str):
        self.api_key = api_key
        self.api_endpoint = api_endpoint

    def compute_pdf_hash(self, pdf_path: str) -> str:
        """Compute SHA256 hash of PDF for cache key."""
        h = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def convert(self, pdf_path: str) -> str:
        """Convert PDF to Markdown.

        Returns:
            Markdown content as string.
        """
        raise NotImplementedError("To be implemented")