"""MinerU API client for PDF to Markdown conversion."""

import asyncio
import hashlib
import io
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

import aiohttp

from argupaper.pdf.types import ConversionResult, TaskStatus
from argupaper.pdf.exceptions import (
    RateLimitError,
    ConversionError,
    ConversionTimeoutError,
    PDFReadError,
)


class MinerUClient:
    """Client for MinerU PDF conversion API."""

    SUBMIT_URL = "https://mineru.net/api/v4/extract/task"

    def __init__(
        self,
        api_key: str,
        model_version: str = "vlm",
        api_endpoint: str | None = None,
    ):
        self.api_key = api_key
        self.model_version = model_version
        self.submit_url = (api_endpoint or self.SUBMIT_URL).rstrip("/")
        self.upload_batch_url = self._build_upload_batch_url()
        self.batch_result_base_url = self._build_batch_result_base_url()
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def supports_local_file_upload(self) -> bool:
        """Whether the configured endpoint supports MinerU v4 signed file upload."""

        return self.submit_url.endswith("/api/v4/extract/task")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                trust_env=True,
            )
        return self._session

    def compute_pdf_hash(self, pdf_path: str | Path) -> str:
        """Compute SHA256 hash of PDF for cache key."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise PDFReadError(f"PDF file not found: {pdf_path}")

        try:
            file_size = pdf_path.stat().st_size
            if file_size == 0:
                raise PDFReadError(f"PDF file is empty: {pdf_path}")
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                raise PDFReadError(f"PDF file too large (>{100}MB): {pdf_path}")
        except OSError as e:
            raise PDFReadError(f"Cannot read PDF file: {pdf_path}, error: {e}")

        h = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def _make_request(
        self,
        method: str,
        url: str,
        json_data: dict | None = None,
        timeout: int = 30,
    ) -> dict:
        """Make an HTTP request to MinerU API."""
        session = await self._get_session()
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        try:
            async with session.request(
                method, url, json=json_data, timeout=timeout_obj
            ) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        "API rate limit exceeded",
                        retry_after=retry_after,
                    )
                if response.status >= 500:
                    raise ConversionError(
                        f"MinerU server error: {response.status}",
                        details={"status": response.status},
                    )

                result = await response.json()

                # Check for API-level errors
                if isinstance(result, dict):
                    if result.get("code") != 0 and result.get("code") != 200:
                        raise ConversionError(
                            f"MinerU API error: {result.get('msg', 'Unknown error')}",
                            details=result,
                        )

                return result

        except aiohttp.ClientError as e:
            raise ConversionError(
                "Network error while connecting to MinerU endpoint "
                f"{url}: {e}. Check MINERU_API_ENDPOINT, network access, "
                "firewall, or HTTP_PROXY/HTTPS_PROXY settings."
            )

    def _build_upload_batch_url(self) -> str:
        if self.submit_url.endswith("/extract/task"):
            return self.submit_url[: -len("/extract/task")] + "/file-urls/batch"
        return self.submit_url.rstrip("/") + "/file-urls/batch"

    def _build_batch_result_base_url(self) -> str:
        if self.submit_url.endswith("/extract/task"):
            return self.submit_url[: -len("/extract/task")] + "/extract-results/batch"
        return self.submit_url.rstrip("/") + "/extract-results/batch"

    async def submit_task(self, pdf_url: str) -> str | dict:
        """Submit a conversion task and return task_id or inline result payload.

        Args:
            pdf_url: URL where the PDF can be accessed

        Returns:
            task_id or inline result payload

        Raises:
            RateLimitError: If API rate limit is exceeded
            ConversionError: If submission fails
        """
        request_body = {
            "url": pdf_url,
            "model_version": self.model_version,
        }

        response = await self._make_request("POST", self.submit_url, json_data=request_body)

        data = self._extract_payload(response)
        if isinstance(data, dict):
            task_id = data.get("task_id") or data.get("id")
            if task_id:
                return str(task_id)

        inline_result = self._extract_inline_result(response)
        if inline_result is not None:
            return inline_result

        raise ConversionError(
            "Could not extract task_id from response",
            details={"response": response},
        )

    async def get_task_result(self, task_id: str) -> dict:
        """Get the result of a conversion task.

        Args:
            task_id: The ID of the task

        Returns:
            dict containing the conversion result
        """
        status_url = f"{self.submit_url}/{task_id}"
        response = await self._make_request("GET", status_url)
        return self._extract_payload(response)

    async def submit_local_file(self, pdf_path: str | Path, data_id: str | None = None) -> str:
        """Upload a local file through MinerU signed upload and return batch_id."""

        path = Path(pdf_path)
        if not path.exists():
            raise PDFReadError(f"PDF file not found: {path}")

        file_item: dict[str, str] = {"name": path.name}
        if data_id:
            file_item["data_id"] = data_id

        request_body = {
            "files": [file_item],
            "model_version": self.model_version,
        }
        response = await self._make_request(
            "POST",
            self.upload_batch_url,
            json_data=request_body,
        )
        data = self._extract_payload(response)
        batch_id = data.get("batch_id") if isinstance(data, dict) else None
        file_urls = data.get("file_urls") if isinstance(data, dict) else None
        if not batch_id or not isinstance(file_urls, list) or not file_urls:
            raise ConversionError(
                "Could not extract batch_id or upload URL from MinerU file upload response",
                details={"response": response},
            )

        await self._upload_file_to_signed_url(str(file_urls[0]), path)
        return str(batch_id)

    async def _upload_file_to_signed_url(self, upload_url: str, path: Path) -> None:
        """Upload a file to MinerU's signed OSS URL without MinerU auth headers."""

        timeout_obj = aiohttp.ClientTimeout(total=300)
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                payload = path.read_bytes()
                async with session.put(
                    upload_url,
                    data=payload,
                    timeout=timeout_obj,
                    skip_auto_headers={"Content-Type"},
                ) as response:
                    if response.status != 200:
                        body = await response.text()
                        body_excerpt = body[:500]
                        raise ConversionError(
                            "Failed to upload PDF to MinerU signed URL: "
                            f"HTTP {response.status}. Response body: {body_excerpt}",
                            details={"status": response.status, "body": body_excerpt},
                        )
        except aiohttp.ClientError as e:
            host = urlparse(upload_url).netloc or upload_url
            raise ConversionError(
                f"Network error while uploading PDF to MinerU signed URL {host}: {e}. "
                "Check network access, firewall, or HTTP_PROXY/HTTPS_PROXY settings."
            )

    async def get_batch_result(self, batch_id: str) -> dict:
        """Get the first local-file extraction result for a batch."""

        response = await self._make_request("GET", f"{self.batch_result_base_url}/{batch_id}")
        data = self._extract_payload(response)
        extract_result = data.get("extract_result") if isinstance(data, dict) else None
        if isinstance(extract_result, list) and extract_result:
            return extract_result[0]
        raise ConversionError(
            "Could not extract batch parse result from MinerU response",
            details={"response": response},
        )

    async def wait_for_batch_completion(
        self,
        batch_id: str,
        poll_interval: float = 2.0,
        max_wait_time: float = 300.0,
    ) -> ConversionResult:
        """Wait for a local-file batch conversion to complete."""

        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            result = await self.get_batch_result(batch_id)
            state = result.get("state") or result.get("status")

            if state in ("SUCCESS", "success", "done"):
                return await self._build_success_result(result)

            if state in ("FAILED", "failed", "error"):
                error_msg = (
                    result.get("error_msg")
                    or result.get("err_msg")
                    or result.get("message")
                    or "Unknown error"
                )
                raise ConversionError(f"Conversion failed: {error_msg}", details=result)

            await asyncio.sleep(poll_interval)

        raise ConversionTimeoutError(
            f"Conversion timed out after {max_wait_time}s",
            timeout_seconds=int(max_wait_time),
        )

    async def convert_local_file(
        self,
        pdf_path: str | Path,
        data_id: str | None = None,
        poll_interval: float = 2.0,
        max_wait_time: float = 300.0,
    ) -> ConversionResult:
        """Convert a local file through MinerU's signed upload flow."""

        batch_id = await self.submit_local_file(pdf_path, data_id=data_id)
        return await self.wait_for_batch_completion(batch_id, poll_interval, max_wait_time)

    async def wait_for_completion(
        self,
        task_id: str | dict,
        poll_interval: float = 2.0,
        max_wait_time: float = 300.0,
    ) -> ConversionResult:
        """Wait for a conversion task to complete.

        Args:
            task_id: The ID of the task
            poll_interval: Seconds between status checks
            max_wait_time: Maximum seconds to wait

        Returns:
            ConversionResult with the converted markdown

        Raises:
            ConversionTimeoutError: If task doesn't complete within timeout
            ConversionError: If task fails
        """
        if isinstance(task_id, dict):
            return await self._build_success_result(task_id)

        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            result = await self.get_task_result(task_id)

            # Parse status from result
            state = result.get("state") or result.get("status")

            # Check for completion states
            if state in ("SUCCESS", "success", "done"):
                return await self._build_success_result(result)

            if state in ("FAILED", "failed", "error"):
                error_msg = result.get("error_msg") or result.get("err_msg") or result.get("message") or "Unknown error"
                raise ConversionError(f"Conversion failed: {error_msg}", details=result)

            # Still processing, wait and poll again
            await asyncio.sleep(poll_interval)

        raise ConversionTimeoutError(
            f"Conversion timed out after {max_wait_time}s",
            timeout_seconds=int(max_wait_time),
        )

    async def _download_and_extract_markdown(self, zip_url: str) -> str:
        """Download ZIP file and extract markdown content.

        Args:
            zip_url: URL to the result ZIP file

        Returns:
            The extracted markdown content as a string
        """
        timeout_obj = aiohttp.ClientTimeout(total=120)  # 2 min for download

        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(zip_url, timeout=timeout_obj) as response:
                    if response.status != 200:
                        raise ConversionError(f"Failed to download result: HTTP {response.status}")

                    zip_data = await response.read()

            # Extract markdown from ZIP
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # Look for markdown files
                md_files = [f for f in zf.namelist() if f.endswith(".md")]
                if md_files:
                    # Return the first markdown file
                    return zf.read(md_files[0]).decode("utf-8")
                else:
                    raise ConversionError(f"No markdown file found in ZIP: {zf.namelist()}")

        except aiohttp.ClientError as e:
            host = urlparse(zip_url).netloc or zip_url
            raise ConversionError(
                f"Failed to download MinerU result from {host}: {e}. "
                "Check network access to MinerU CDN, firewall, or HTTP_PROXY/HTTPS_PROXY settings."
            )
        except zipfile.BadZipFile:
            raise ConversionError(f"Downloaded file is not a valid ZIP")

    async def convert(
        self,
        pdf_url: str,
        poll_interval: float = 2.0,
        max_wait_time: float = 300.0,
    ) -> ConversionResult:
        """Convert a PDF to Markdown.

        This is a convenience method that submits the task and waits for completion.

        Args:
            pdf_url: URL where the PDF can be accessed
            poll_interval: Seconds between status checks
            max_wait_time: Maximum seconds to wait

        Returns:
            ConversionResult with the converted markdown
        """
        task_id = await self.submit_task(pdf_url)
        result = await self.wait_for_completion(task_id, poll_interval, max_wait_time)
        return result

    def _extract_payload(self, response: dict) -> dict:
        data = response.get("data")
        if isinstance(data, dict):
            return data
        return response

    def _extract_inline_result(self, response: dict) -> dict | None:
        for payload in (self._extract_payload(response), response):
            if not isinstance(payload, dict):
                continue
            if payload.get("markdown") or payload.get("content"):
                return payload
            if payload.get("state") in ("SUCCESS", "success", "done") and payload.get("full_zip_url"):
                return payload
        return None

    async def _build_success_result(self, payload: dict) -> ConversionResult:
        zip_url = payload.get("full_zip_url")
        markdown_url = payload.get("markdown_url")
        markdown = str(payload.get("markdown") or payload.get("content") or "")
        if zip_url:
            markdown = await self._download_and_extract_markdown(str(zip_url))
        elif markdown_url:
            markdown = await self._download_markdown(str(markdown_url))
        return ConversionResult(
            status=TaskStatus.SUCCESS,
            markdown=markdown,
            cache_key="",
        )

    async def _download_markdown(self, markdown_url: str) -> str:
        timeout_obj = aiohttp.ClientTimeout(total=120)

        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(markdown_url, timeout=timeout_obj) as response:
                    if response.status != 200:
                        raise ConversionError(f"Failed to download markdown: HTTP {response.status}")
                    return await response.text()
        except aiohttp.ClientError as e:
            host = urlparse(markdown_url).netloc or markdown_url
            raise ConversionError(
                f"Failed to download MinerU markdown from {host}: {e}. "
                "Check network access to MinerU CDN, firewall, or HTTP_PROXY/HTTPS_PROXY settings."
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "MinerUClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
