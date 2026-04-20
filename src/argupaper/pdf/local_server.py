"""Local HTTP server for exposing PDF files to MinerU API."""

import asyncio
import socket
from pathlib import Path
from typing import Optional

from aiohttp import web

from argupaper.pdf.exceptions import ServerError, URLUploadError


class LocalPDFServer:
    """Local HTTP server that serves PDF files for MinerU to access.

    This server is designed to run temporarily while a conversion task
    is in progress, exposing local PDF files via HTTP URL.
    """

    def __init__(self, host: str = "localhost", port: Optional[int] = None):
        """Initialize the server.

        Args:
            host: Host to bind to (default: localhost)
            port: Port to bind to (None = auto-select available port)
        """
        self.host = host
        self.port = port
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._pdf_paths: dict[str, Path] = {}  # cache_key -> pdf_path
        self._actual_port: Optional[int] = None

    async def start(self) -> None:
        """Start the HTTP server."""
        if self._runner is not None:
            return  # Already started

        self._app = web.Application()

        # Add routes
        self._app.router.add_get("/pdf/{cache_key}", self._handle_pdf_request)
        self._app.router.add_get("/health", self._handle_health)

        # Setup runner
        self._runner = web.AppRunner(self._app)

        try:
            await self._runner.setup()

            # Find an available port if not specified
            if self.port is None:
                # Create a temporary socket to find an available port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind((self.host, 0))
                self._actual_port = sock.getsockname()[1]
                sock.close()
            else:
                self._actual_port = self.port

            # Create site
            self._site = web.TCPSite(self._runner, self.host, self._actual_port)
            await self._site.start()

        except OSError as e:
            raise ServerError(f"Failed to start HTTP server: {e}")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._app = None
            self._site = None
            self._actual_port = None

    def register_pdf(self, cache_key: str, pdf_path: Path) -> None:
        """Register a PDF file to be served.

        Args:
            cache_key: Unique identifier for this PDF
            pdf_path: Path to the PDF file
        """
        if not pdf_path.exists():
            raise URLUploadError(f"PDF file not found: {pdf_path}")
        self._pdf_paths[cache_key] = pdf_path

    def get_url_for_pdf(self, cache_key: str) -> str:
        """Get the URL for a registered PDF.

        Args:
            cache_key: Unique identifier for the PDF

        Returns:
            The URL where MinerU can access the PDF

        Raises:
            URLUploadError: If server is not running or PDF not registered
        """
        if self._actual_port is None:
            raise URLUploadError("Server is not running. Call start() first.")
        if cache_key not in self._pdf_paths:
            raise URLUploadError(f"PDF not registered: {cache_key}")
        return f"http://{self.host}:{self._actual_port}/pdf/{cache_key}"

    async def _handle_pdf_request(self, request: web.Request) -> web.Response:
        """Handle request for a PDF file."""
        cache_key = request.match_info.get("cache_key")

        if cache_key is None or cache_key not in self._pdf_paths:
            return web.Response(status=404, text="PDF not found")

        pdf_path = self._pdf_paths[cache_key]

        try:
            return web.FileResponse(pdf_path, headers={"Content-Type": "application/pdf"})
        except FileNotFoundError:
            return web.Response(status=404, text="PDF file not found")

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle health check request."""
        return web.Response(text="OK")

    async def __aenter__(self) -> "LocalPDFServer":
        """Start server on context entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop server on context exit."""
        await self.stop()
