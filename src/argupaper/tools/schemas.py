"""Common tool input and output schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Generic result envelope for future Agent-callable tools."""

    ok: bool = True
    data: Any = None
    warnings: list[str] = Field(default_factory=list)


__all__ = ["ToolResult"]

