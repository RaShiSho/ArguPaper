"""Tests for MinerUClient."""

from __future__ import annotations

from pathlib import Path

import pytest

from argupaper.pdf.exceptions import PDFReadError
from argupaper.pdf.mineru_client import MinerUClient


@pytest.fixture
def mineru_client():
    """Create a MinerUClient instance."""
    return MinerUClient(api_key="test-api-key")


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test.pdf"
    # Create a minimal PDF content
    pdf_path.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    return pdf_path


class TestMinerUClient:
    """Tests for MinerUClient class."""

    def test_compute_pdf_hash(self, mineru_client, sample_pdf_path):
        """Test SHA256 hash computation is consistent."""
        hash1 = mineru_client.compute_pdf_hash(sample_pdf_path)
        hash2 = mineru_client.compute_pdf_hash(sample_pdf_path)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters

    def test_compute_pdf_hash_nonexistent(self, mineru_client):
        """Test hash computation on non-existent file raises error."""
        with pytest.raises(PDFReadError, match="PDF file not found"):
            mineru_client.compute_pdf_hash("/nonexistent/path.pdf")

    def test_compute_pdf_hash_empty_file(self, mineru_client, tmp_path):
        """Test hash computation on empty file raises error."""
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with pytest.raises(PDFReadError, match="PDF file is empty"):
            mineru_client.compute_pdf_hash(empty_pdf)

    def test_compute_pdf_hash_accepts_string(self, mineru_client, sample_pdf_path):
        """Test that compute_pdf_hash accepts string path."""
        hash1 = mineru_client.compute_pdf_hash(str(sample_pdf_path))
        hash2 = mineru_client.compute_pdf_hash(sample_pdf_path)

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_submit_task_preserves_inline_markdown_response(self) -> None:
        """Inline MinerU responses should not be converted into fake task ids."""

        client = MinerUClient(api_key="test-api-key")
        request_calls: list[tuple[str, str]] = []

        async def fake_make_request(method: str, url: str, json_data=None, timeout: int = 30) -> dict:
            request_calls.append((method, url))
            return {"code": 0, "data": {"markdown": "# Inline Markdown"}}

        client._make_request = fake_make_request  # type: ignore[method-assign]

        task_or_result = await client.submit_task("https://example.com/paper.pdf")
        result = await client.wait_for_completion(task_or_result)

        assert result.markdown == "# Inline Markdown"
        assert request_calls == [("POST", client.submit_url)]

    @pytest.mark.asyncio
    async def test_custom_endpoint_is_used_for_submit_and_status_requests(self) -> None:
        """Configured endpoint should be used instead of the hard-coded default."""

        client = MinerUClient(
            api_key="test-api-key",
            api_endpoint="https://mineru.example.com/v1/convert/",
        )
        request_calls: list[tuple[str, str]] = []

        async def fake_make_request(method: str, url: str, json_data=None, timeout: int = 30) -> dict:
            request_calls.append((method, url))
            if method == "POST":
                return {"code": 0, "data": {"task_id": "task-123"}}
            return {"code": 0, "data": {"status": "success", "markdown": "# Completed"}}

        client._make_request = fake_make_request  # type: ignore[method-assign]

        task_id = await client.submit_task("https://example.com/paper.pdf")
        result = await client.wait_for_completion(task_id)

        assert client.submit_url == "https://mineru.example.com/v1/convert"
        assert result.markdown == "# Completed"
        assert request_calls == [
            ("POST", "https://mineru.example.com/v1/convert"),
            ("GET", "https://mineru.example.com/v1/convert/task-123"),
        ]
