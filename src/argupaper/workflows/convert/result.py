"""Convert workflow result models."""

from pathlib import Path

from pydantic import BaseModel

from argupaper.services.pdf import ConversionResult


class FolderConvertSummary(BaseModel):
    """Summary for folder conversion."""

    total_entries: int = 0
    processed: int = 0
    success: int = 0
    cache_hits: int = 0
    failed: int = 0
    skipped: int = 0


class ConvertWorkflowResult(BaseModel):
    """Result for single-file or folder conversion."""

    conversion: ConversionResult | None = None
    summary: FolderConvertSummary | None = None
    input_path: Path | None = None
    cache_path: Path | None = None
    output_path: Path | None = None
    run_log_path: Path | None = None


__all__ = ["ConvertWorkflowResult", "FolderConvertSummary"]

