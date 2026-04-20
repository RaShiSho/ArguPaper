"""Type definitions for PDF processing pipeline."""

from pydantic import BaseModel
from pathlib import Path
from enum import Enum
from datetime import datetime
from typing import Optional


class TaskStatus(str, Enum):
    """Status of a MinerU conversion task."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class ConversionResult(BaseModel):
    """Result of a PDF to Markdown conversion."""
    status: TaskStatus
    markdown: Optional[str] = None
    cache_key: str
    error: Optional[str] = None
    from_cache: bool = False


class MinerURequest(BaseModel):
    """MinerU API request body."""
    url: str
    model_version: str = "vlm"


class MinerUResponse(BaseModel):
    """MinerU API response structure."""
    code: int
    msg: str
    data: Optional[dict] = None


class PDFDocument(BaseModel):
    """Metadata for a PDF document."""
    pdf_path: Path
    cache_key: str
    file_size: int
    title: Optional[str] = None
    created_at: Optional[datetime] = None


class CacheMetadata(BaseModel):
    """Metadata stored alongside cached Markdown."""
    original_filename: str
    converted_at: datetime
    file_size: int
    mineru_version: str = "vlm"
