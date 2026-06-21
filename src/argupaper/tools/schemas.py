"""Common tool input and output schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Generic result envelope for Agent-callable tools."""

    tool: str = ""
    ok: bool = True
    summary: str = ""
    data: Any = None
    warnings: list[str] = Field(default_factory=list)


class ListPapersArgs(BaseModel):
    """Arguments for listing or searching saved papers."""

    query: str | None = Field(default=None, description="Optional local library search text.")
    limit: int = Field(default=20, ge=1, le=50)


class SelectPaperArgs(BaseModel):
    """Arguments for selecting a saved paper."""

    paper: str = Field(description="Paper id, unique id prefix, title, source, or search text.")


class DebatePaperArgs(BaseModel):
    """Arguments for running multi-agent debate analysis for one paper."""

    paper_id: str | None = Field(default=None, description="Paper id. Defaults to selected paper.")
    rounds: int = Field(default=3, ge=1, le=8)


class CourtPaperArgs(BaseModel):
    """Arguments for running adversarial paper court review for one paper."""

    paper_id: str | None = Field(default=None, description="Paper id. Defaults to selected paper.")
    max_rounds: int = Field(default=2, ge=1, le=8)


class SearchPapersArgs(BaseModel):
    """Arguments for external paper search."""

    query: str
    limit: int = Field(default=10, ge=1, le=50)
    source: str = Field(default="both")


class ReadPaperContextArgs(BaseModel):
    """Arguments for reading selected paper context."""

    paper_id: str | None = Field(default=None, description="Paper id. Defaults to selected paper.")
    max_chars: int = Field(default=6000, ge=500, le=20000)


class ReadPaperFullTextArgs(BaseModel):
    """Arguments for reading selected paper full markdown."""

    paper_id: str | None = Field(default=None, description="Paper id. Defaults to selected paper.")
    max_chars: int | None = Field(
        default=None,
        ge=1,
        le=500000,
        description="Optional maximum characters to return from paper markdown.",
    )
    include_report: bool = Field(
        default=False,
        description="Whether to include the local analysis report text when available.",
    )


__all__ = [
    "DebatePaperArgs",
    "CourtPaperArgs",
    "ListPapersArgs",
    "ReadPaperContextArgs",
    "ReadPaperFullTextArgs",
    "SearchPapersArgs",
    "SelectPaperArgs",
    "ToolResult",
]
