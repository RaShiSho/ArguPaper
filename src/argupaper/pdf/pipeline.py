"""PDF processing pipeline integrating all PDF components."""

import asyncio
from pathlib import Path
from typing import Optional

from argupaper.pdf.mineru_client import MinerUClient
from argupaper.pdf.cache import MarkdownCache
from argupaper.pdf.local_server import LocalPDFServer
from argupaper.pdf.types import ConversionResult, TaskStatus
from argupaper.pdf.exceptions import (
    PDFPipelineError,
    PDFReadError,
    RateLimitError,
    ConversionError,
)


class PDFPipeline:
    """Pipeline for converting PDF files to Markdown using MinerU.

    This pipeline:
    1. Computes a hash of the PDF for cache key
    2. Checks local cache for existing conversion
    3. Starts a local HTTP server to serve the PDF
    4. Submits conversion task to MinerU
    5. Polls for completion and returns result
    6. Caches the result for future use
    """

    def __init__(
        self,
        mineru_client: MinerUClient,
        cache: MarkdownCache,
        local_server: Optional[LocalPDFServer] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
        retry_multiplier: float = 2.0,
        public_url_base: Optional[str] = None,
    ):
        """Initialize the pipeline.

        Args:
            mineru_client: MinerU API client
            cache: Markdown cache
            local_server: Local HTTP server (creates default if None)
            max_retries: Maximum number of retries on rate limit
            initial_retry_delay: Initial delay between retries (seconds)
            max_retry_delay: Maximum delay between retries (seconds)
            retry_multiplier: Multiplier for exponential backoff
            public_url_base: Public URL base for ngrok/tunnel (e.g., "https://xxxx.ngrok-free.dev")
        """
        self.mineru = mineru_client
        self.cache = cache
        self.public_url_base = public_url_base

        # Use port 8080 for ngrok compatibility
        if public_url_base and local_server is None:
            self.local_server = LocalPDFServer(port=8080)
        else:
            self.local_server = local_server or LocalPDFServer()

        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.retry_multiplier = retry_multiplier

    async def process(
        self,
        pdf_path: str | Path,
        force_reconvert: bool = False,
    ) -> ConversionResult:
        """Process a PDF file and convert to Markdown.

        Args:
            pdf_path: Path to the PDF file
            force_reconvert: If True, ignore cache and reconvert

        Returns:
            ConversionResult containing the Markdown or error

        Raises:
            PDFReadError: If PDF cannot be read
            RateLimitError: If API rate limit is exceeded after retries
            ConversionError: If conversion fails
        """
        pdf_path = Path(pdf_path)

        # Validate PDF exists
        if not pdf_path.exists():
            raise PDFReadError(f"PDF file not found: {pdf_path}")

        # Compute cache key
        cache_key = self.mineru.compute_pdf_hash(pdf_path)

        # Check cache first (unless force_reconvert)
        if not force_reconvert:
            cached_markdown = self.cache.get(cache_key)
            if cached_markdown is not None:
                return ConversionResult(
                    status=TaskStatus.SUCCESS,
                    markdown=cached_markdown,
                    cache_key=cache_key,
                    from_cache=True,
                )

        # Get file size for metadata
        file_size = pdf_path.stat().st_size
        filename = pdf_path.name

        # Convert with retry logic for rate limits
        result = await self._convert_with_retry(
            pdf_path, cache_key, filename, file_size
        )

        return result

    async def _convert_with_retry(
        self,
        pdf_path: Path,
        cache_key: str,
        filename: str,
        file_size: int,
    ) -> ConversionResult:
        """Convert PDF with exponential backoff retry on rate limit.

        Args:
            pdf_path: Path to the PDF file
            cache_key: Cache key (SHA256 hash)
            filename: Original filename
            file_size: File size in bytes

        Returns:
            ConversionResult
        """
        delay = self.initial_retry_delay
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                # Register PDF with local server
                self.local_server.register_pdf(cache_key, pdf_path)

                # Start server and get URL
                async with self.local_server:
                    if self.public_url_base:
                        # Use public URL base (ngrok/tunnel)
                        pdf_url = f"{self.public_url_base}/pdf/{cache_key}"
                    else:
                        # Use local server URL
                        pdf_url = self.local_server.get_url_for_pdf(cache_key)

                    # Submit and wait for conversion
                    result = await self.mineru.wait_for_completion(
                        await self.mineru.submit_task(pdf_url)
                    )

                # Update result with cache key and store in cache
                result.cache_key = cache_key

                if result.markdown:
                    self.cache.set(
                        cache_key=cache_key,
                        markdown=result.markdown,
                        original_filename=filename,
                        file_size=file_size,
                    )

                return result

            except RateLimitError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * self.retry_multiplier, self.max_retry_delay)
                continue

            except (PDFPipelineError, ConversionError) as e:
                last_error = e
                break

        # All retries exhausted or non-retryable error
        if last_error:
            if isinstance(last_error, RateLimitError):
                raise last_error
            raise ConversionError(
                f"Conversion failed after {self.max_retries} attempts: {last_error}"
            )

        # Should not reach here
        raise ConversionError("Unexpected error in conversion")

    async def close(self) -> None:
        """Close resources (HTTP session, etc.)."""
        await self.mineru.close()

    async def __aenter__(self) -> "PDFPipeline":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
