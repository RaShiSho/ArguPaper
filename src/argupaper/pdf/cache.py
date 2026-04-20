"""Local caching for converted Markdown files."""

import json
from pathlib import Path
from typing import Optional

from argupaper.pdf.types import CacheMetadata
from argupaper.pdf.exceptions import CacheError


class MarkdownCache:
    """Cache for PDF -> Markdown conversion results.

    Caches are stored in the following structure:
        cache_dir/
            {sha256_hash}.md           # The converted markdown
            {sha256_hash}.meta.json   # Metadata about the conversion
    """

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(f"Cannot create cache directory: {self.cache_dir}, error: {e}")

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the path to a cached markdown file."""
        return self.cache_dir / f"{cache_key}.md"

    def _get_meta_path(self, cache_key: str) -> Path:
        """Get the path to a cache metadata file."""
        return self.cache_dir / f"{cache_key}.meta.json"

    def exists(self, cache_key: str) -> bool:
        """Check if a cache entry exists."""
        cache_path = self._get_cache_path(cache_key)
        return cache_path.exists()

    def get(self, cache_key: str) -> Optional[str]:
        """Get cached Markdown content if it exists.

        Args:
            cache_key: SHA256 hash of the PDF

        Returns:
            The cached Markdown content as a string, or None if not cached
        """
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            # Verify the file is readable and not empty
            content = cache_path.read_text(encoding="utf-8")
            if not content.strip():
                # Empty file, treat as cache miss
                self._remove_broken_cache(cache_key)
                return None
            return content
        except UnicodeDecodeError as e:
            # File is corrupted (not valid UTF-8)
            self._remove_broken_cache(cache_key)
            return None
        except OSError as e:
            # File read error
            raise CacheError(f"Cannot read cache file: {cache_path}, error: {e}")

    def _remove_broken_cache(self, cache_key: str) -> None:
        """Remove a broken cache entry."""
        try:
            cache_path = self._get_cache_path(cache_key)
            meta_path = self._get_meta_path(cache_key)
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        except OSError:
            pass  # Best effort cleanup

    def set(
        self,
        cache_key: str,
        markdown: str,
        original_filename: str = "",
        file_size: int = 0,
    ) -> None:
        """Store Markdown content in cache.

        Args:
            cache_key: SHA256 hash of the PDF
            markdown: The converted Markdown content
            original_filename: Original PDF filename for metadata
            file_size: Original PDF file size
        """
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        try:
            # Write markdown content
            cache_path.write_text(markdown, encoding="utf-8")

            # Write metadata
            from datetime import datetime

            metadata = CacheMetadata(
                original_filename=original_filename,
                converted_at=datetime.now(),
                file_size=file_size,
            )
            meta_path.write_text(metadata.model_dump_json(), encoding="utf-8")

        except OSError as e:
            # Cleanup on failure
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            raise CacheError(f"Cannot write cache file: {cache_path}, error: {e}")

    def invalidate(self, cache_key: str) -> None:
        """Remove a cache entry.

        Args:
            cache_key: SHA256 hash of the PDF
        """
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        try:
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        except OSError as e:
            raise CacheError(f"Cannot remove cache file: {cache_path}, error: {e}")

    def get_metadata(self, cache_key: str) -> Optional[CacheMetadata]:
        """Get metadata for a cached entry.

        Args:
            cache_key: SHA256 hash of the PDF

        Returns:
            CacheMetadata if cache exists, None otherwise
        """
        meta_path = self._get_meta_path(cache_key)

        if not meta_path.exists():
            return None

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return CacheMetadata(**data)
        except (OSError, json.JSONDecodeError) as e:
            return None

    def get_cache_stats(self) -> dict:
        """Get statistics about the cache.

        Returns:
            dict with keys: total_entries, total_size_bytes, oldest_entry, newest_entry
        """
        stats = {
            "total_entries": 0,
            "total_size_bytes": 0,
            "oldest_entry": None,
            "newest_entry": None,
        }

        try:
            md_files = list(self.cache_dir.glob("*.md"))
            meta_files = list(self.cache_dir.glob("*.meta.json"))

            stats["total_entries"] = len(md_files)

            total_size = 0
            oldest_time = None
            newest_time = None

            for meta_file in meta_files:
                try:
                    size = meta_file.stat().st_size
                    total_size += size

                    # Read timestamp from metadata
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    converted_at = data.get("converted_at")
                    if converted_at:
                        from datetime import datetime

                        dt = datetime.fromisoformat(converted_at.replace("Z", "+00:00"))
                        if oldest_time is None or dt < oldest_time:
                            oldest_time = dt
                        if newest_time is None or dt > newest_time:
                            newest_time = dt
                except (OSError, json.JSONDecodeError):
                    continue

            stats["total_size_bytes"] = total_size
            stats["oldest_entry"] = oldest_time.isoformat() if oldest_time else None
            stats["newest_entry"] = newest_time.isoformat() if newest_time else None

        except OSError as e:
            raise CacheError(f"Cannot read cache directory: {self.cache_dir}, error: {e}")

        return stats

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.md"):
                cache_file.unlink()
                count += 1
            for meta_file in self.cache_dir.glob("*.meta.json"):
                meta_file.unlink()
        except OSError as e:
            raise CacheError(f"Cannot clear cache directory: {self.cache_dir}, error: {e}")
        return count
