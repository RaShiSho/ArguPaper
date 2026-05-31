"""Agent-callable tool wrappers."""

from argupaper.tools.factory import build_default_tool_registry, build_default_toolbox
from argupaper.tools.registry import LangChainToolbox, RegisteredTool, ToolRegistry
from argupaper.tools.schemas import (
    AnalyzePaperArgs,
    ListPapersArgs,
    ReadPaperContextArgs,
    SearchPapersArgs,
    SelectPaperArgs,
    ToolResult,
)

__all__ = [
    "AnalyzePaperArgs",
    "LangChainToolbox",
    "ListPapersArgs",
    "ReadPaperContextArgs",
    "RegisteredTool",
    "SearchPapersArgs",
    "SelectPaperArgs",
    "ToolRegistry",
    "ToolResult",
    "build_default_tool_registry",
    "build_default_toolbox",
]
