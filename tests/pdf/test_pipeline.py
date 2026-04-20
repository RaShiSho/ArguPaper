"""Tests for PDFPipeline."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from argupaper.pdf.pipeline import PDFPipeline
from argupaper.pdf.mineru_client import MinerUClient
from argupaper.pdf.cache import MarkdownCache
from argupaper.pdf.local_server import LocalPDFServer
from argupaper.pdf.types import ConversionResult, TaskStatus
from argupaper.pdf.exceptions import PDFReadError


@pytest.fixture
def mock_mineru():
    """Create a mock MinerU client."""
    client = MagicMock(spec=MinerUClient)
    client.compute_pdf_hash.return_value = "abc123"
    client.submit_task = AsyncMock(return_value="task-123")
    client.wait_for_completion = AsyncMock(
        return_value=ConversionResult(
            status=TaskStatus.SUCCESS,
            markdown="# Converted Markdown",
            cache_key="abc123",
        )
    )
    client.close = AsyncMock()
    return client


@pytest.fixture
def cache(tmp_path):
    """Create a cache instance."""
    return MarkdownCache(cache_dir=str(tmp_path))


@pytest.fixture
def server():
    """Create a local server instance."""
    return LocalPDFServer()


@pytest.fixture
def pipeline(mock_mineru, cache, server):
    """Create a PDFPipeline instance."""
    return PDFPipeline(mock_mineru, cache, server)


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    return pdf_path


class TestPDFPipeline:
    """Tests for PDFPipeline class."""

    @pytest.mark.asyncio
    async def test_process_cache_hit(self, pipeline, sample_pdf):
        """Test that cached results are returned without API call."""
        # Pre-populate cache
        pipeline.cache.set("abc123", "# Cached Content", "test.pdf", 100)

        result = await pipeline.process(sample_pdf)

        assert result.from_cache is True
        assert result.markdown == "# Cached Content"
        assert result.cache_key == "abc123"
        # API should not have been called
        pipeline.mineru.submit_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_cache_miss(self, pipeline, sample_pdf):
        """Test that API is called on cache miss."""
        result = await pipeline.process(sample_pdf)

        assert result.from_cache is False
        assert result.markdown == "# Converted Markdown"
        pipeline.mineru.submit_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_stores_result(self, pipeline, sample_pdf):
        """Test that conversion result is cached."""
        await pipeline.process(sample_pdf)

        cached = pipeline.cache.get("abc123")
        assert cached == "# Converted Markdown"

    @pytest.mark.asyncio
    async def test_process_nonexistent_file(self, pipeline):
        """Test that nonexistent file raises error."""
        with pytest.raises(PDFReadError, match="not found"):
            await pipeline.process("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_process_force_reconvert(self, pipeline, sample_pdf):
        """Test force_reconvert ignores cache."""
        # Pre-populate cache
        pipeline.cache.set("abc123", "# Old Content", "test.pdf", 100)

        result = await pipeline.process(sample_pdf, force_reconvert=True)

        # Should call API even though cache exists
        pipeline.mineru.submit_task.assert_called_once()
        assert result.markdown == "# Converted Markdown"

    @pytest.mark.asyncio
    async def test_close(self, pipeline):
        """Test close() is called on mineru client."""
        await pipeline.close()
        pipeline.mineru.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_mineru, cache, server):
        """Test pipeline as context manager."""
        async with PDFPipeline(mock_mineru, cache, server) as p:
            pass
        mock_mineru.close.assert_called_once()
