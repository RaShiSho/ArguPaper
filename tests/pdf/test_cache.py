"""Tests for MarkdownCache."""

import pytest
import json
from pathlib import Path
from argupaper.pdf.cache import MarkdownCache
from argupaper.pdf.exceptions import CacheError


@pytest.fixture
def cache(tmp_path):
    """Create a MarkdownCache instance with temporary directory."""
    return MarkdownCache(cache_dir=str(tmp_path))


@pytest.fixture
def populated_cache(tmp_path):
    """Create a cache with some entries."""
    cache = MarkdownCache(cache_dir=str(tmp_path))
    cache.set("abc123", "# Test Markdown\n\nContent here.", "test.pdf", 1024)
    return cache


class TestMarkdownCache:
    """Tests for MarkdownCache class."""

    def test_get_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get("nonexistent-key")
        assert result is None

    def test_set_and_get_cache(self, cache):
        """Test setting and getting cache."""
        cache.set("test-key", "# Markdown Content", "test.pdf", 2048)
        result = cache.get("test-key")
        assert result == "# Markdown Content"

    def test_cache_with_special_characters(self, cache):
        """Test cache handles special characters correctly."""
        markdown = "# Title\n\n中文内容\n## 标题\n```python\ncode()\n```"
        cache.set("special-key", markdown, "test.pdf", 100)
        result = cache.get("special-key")
        assert result == markdown

    def test_exists(self, cache):
        """Test exists() returns correct values."""
        assert not cache.exists("nonexistent")
        cache.set("exists-key", "content")
        assert cache.exists("exists-key")

    def test_invalidate(self, cache):
        """Test invalidating cache entries."""
        cache.set("to-delete", "content")
        assert cache.exists("to-delete")

        cache.invalidate("to-delete")
        assert not cache.exists("to-delete")

    def test_invalidate_nonexistent(self, cache):
        """Test invalidating nonexistent key doesn't raise."""
        cache.invalidate("nonexistent")  # Should not raise

    def test_get_metadata(self, cache):
        """Test metadata is stored correctly."""
        cache.set("meta-key", "content", "original.pdf", 4096)
        metadata = cache.get_metadata("meta-key")

        assert metadata is not None
        assert metadata.original_filename == "original.pdf"
        assert metadata.file_size == 4096

    def test_get_metadata_nonexistent(self, cache):
        """Test metadata for nonexistent key returns None."""
        metadata = cache.get_metadata("nonexistent")
        assert metadata is None

    def test_get_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "content1", "file1.pdf", 100)
        cache.set("key2", "content2", "file2.pdf", 200)

        stats = cache.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["total_size_bytes"] > 0
        assert stats["oldest_entry"] is not None
        assert stats["newest_entry"] is not None

    def test_clear(self, populated_cache):
        """Test clearing all cache entries."""
        assert populated_cache.exists("abc123")
        count = populated_cache.clear()
        assert count >= 1
        assert not populated_cache.exists("abc123")

    def test_empty_markdown_treated_as_miss(self, cache, tmp_path):
        """Test that empty markdown content is treated as cache miss."""
        cache.set("empty", "", "test.pdf", 0)
        # Empty file should be cleaned up
        assert cache.get("empty") is None

    def test_corrupted_markdown_treated_as_miss(self, cache, tmp_path):
        """Test that corrupted markdown content is treated as cache miss."""
        # Directly write a corrupted file
        cache_path = cache._get_cache_path("corrupted")
        cache_path.write_bytes(b"\xff\xfe\xfd")  # Invalid UTF-8

        # Should treat as miss and clean up
        assert cache.get("corrupted") is None
