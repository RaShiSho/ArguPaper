"""Tests for LocalPDFServer."""

import pytest
from pathlib import Path
from argupaper.pdf.local_server import LocalPDFServer
from argupaper.pdf.exceptions import URLUploadError


@pytest.fixture
def server():
    """Create a LocalPDFServer instance."""
    return LocalPDFServer()


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest content")
    return pdf_path


class TestLocalPDFServer:
    """Tests for LocalPDFServer class."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self, server):
        """Test server can start and stop."""
        await server.start()
        assert server._actual_port is not None
        await server.stop()
        assert server._actual_port is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test server as context manager."""
        async with LocalPDFServer() as server:
            assert server._actual_port is not None
        # Server should be stopped after context

    @pytest.mark.asyncio
    async def test_register_pdf(self, server, sample_pdf):
        """Test registering a PDF file."""
        await server.start()
        try:
            server.register_pdf("test-key", sample_pdf)
            url = server.get_url_for_pdf("test-key")
            assert "test-key" in url
            assert url.startswith("http://")
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_get_url_before_start(self, server, sample_pdf):
        """Test getting URL before server starts raises error."""
        server.register_pdf("test-key", sample_pdf)
        with pytest.raises(URLUploadError, match="not running"):
            server.get_url_for_pdf("test-key")

    @pytest.mark.asyncio
    async def test_get_url_unregistered_key(self, server):
        """Test getting URL for unregistered key raises error."""
        await server.start()
        try:
            with pytest.raises(URLUploadError, match="not registered"):
                server.get_url_for_pdf("nonexistent")
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_register_nonexistent_pdf(self, server):
        """Test registering nonexistent file raises error."""
        with pytest.raises(URLUploadError, match="not found"):
            server.register_pdf("bad-key", Path("/nonexistent/file.pdf"))
