"""PDF processing with MinerU API and local caching."""

from argupaper.pdf.mineru_client import MinerUClient
from argupaper.pdf.cache import MarkdownCache
from argupaper.pdf.local_server import LocalPDFServer
from argupaper.pdf.pipeline import PDFPipeline
from argupaper.pdf.types import (
    TaskStatus,
    ConversionResult,
    MinerURequest,
    MinerUResponse,
    PDFDocument,
    CacheMetadata,
)
from argupaper.pdf.exceptions import (
    PDFPipelineError,
    PDFReadError,
    URLUploadError,
    RateLimitError,
    ConversionError,
    ConversionTimeoutError,
    CacheError,
    ServerError,
)

__all__ = [
    # Client
    "MinerUClient",
    "MarkdownCache",
    "LocalPDFServer",
    "PDFPipeline",
    # Types
    "TaskStatus",
    "ConversionResult",
    "MinerURequest",
    "MinerUResponse",
    "PDFDocument",
    "CacheMetadata",
    # Exceptions
    "PDFPipelineError",
    "PDFReadError",
    "URLUploadError",
    "RateLimitError",
    "ConversionError",
    "ConversionTimeoutError",
    "CacheError",
    "ServerError",
]