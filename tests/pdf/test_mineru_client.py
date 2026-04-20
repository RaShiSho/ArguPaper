"""Tests for MinerUClient."""

import pytest
from pathlib import Path
from argupaper.pdf.mineru_client import MinerUClient
from argupaper.pdf.exceptions import PDFReadError


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
