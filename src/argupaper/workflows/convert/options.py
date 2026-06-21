"""Convert workflow options."""

from pathlib import Path

from pydantic import BaseModel


class ConvertOptions(BaseModel):
    """Options for PDF to Markdown conversion."""

    pdf_path: Path | None = None
    folder_path: Path | None = None
    output_path: Path | None = None
    force_reconvert: bool = False


__all__ = ["ConvertOptions"]

