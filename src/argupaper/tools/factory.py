"""Default Agent tool registry construction."""

from __future__ import annotations

from collections.abc import Callable

from argupaper.config import Config
from argupaper.tools.paper_tools import register_paper_tools
from argupaper.tools.registry import LangChainToolbox, ToolRegistry
from argupaper.tools.workflow_tools import register_workflow_tools

ProgressCallback = Callable[[str], None] | None


def build_default_tool_registry(
    config: Config,
    progress_callback: ProgressCallback = None,
) -> ToolRegistry:
    """Build the default registry of Agent-callable tools."""

    registry = ToolRegistry()
    register_paper_tools(registry, config, progress_callback=progress_callback)
    register_workflow_tools(registry, config, progress_callback=progress_callback)
    return registry


def build_default_toolbox(
    config: Config,
    progress_callback: ProgressCallback = None,
) -> LangChainToolbox:
    """Build the default LangChain toolbox for Agent runtimes."""

    return LangChainToolbox(build_default_tool_registry(config, progress_callback=progress_callback))


__all__ = ["build_default_tool_registry", "build_default_toolbox"]
