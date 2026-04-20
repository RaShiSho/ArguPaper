"""Local caching for converted Markdown files."""

from pathlib import Path
from typing import Optional


class MarkdownCache:
    """Cache for PDF -> Markdown conversion results."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, cache_key: str) -> Optional[str]:
        """Get cached Markdown if exists."""
        raise NotImplementedError("To be implemented")

    def set(self, cache_key: str, markdown: str) -> None:
        """Store Markdown in cache."""
        raise NotImplementedError("To be implemented")

    def invalidate(self, cache_key: str) -> None:
        """Remove item from cache."""
        raise NotImplementedError("To be implemented")