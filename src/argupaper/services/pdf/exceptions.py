"""Custom exceptions for PDF processing pipeline."""


class PDFPipelineError(Exception):
    """Base exception for PDF pipeline errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PDFReadError(PDFPipelineError):
    """Raised when PDF file cannot be read."""

    pass


class URLUploadError(PDFPipelineError):
    """Raised when PDF cannot be exposed via URL."""

    pass


class RateLimitError(PDFPipelineError):
    """Raised when API rate limit is hit."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class ConversionError(PDFPipelineError):
    """Raised when conversion fails."""

    pass


class ConversionTimeoutError(ConversionError):
    """Raised when conversion times out."""

    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class CacheError(PDFPipelineError):
    """Raised when cache operations fail."""

    pass


class ServerError(PDFPipelineError):
    """Raised when local HTTP server fails."""

    pass
