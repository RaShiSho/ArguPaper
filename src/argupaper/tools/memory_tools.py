"""Conversation and paper-memory tool wrappers for future supervisor agents."""

from argupaper.tools.registry import ToolRegistry


def register_memory_tools(registry: ToolRegistry) -> None:
    """Register memory tools in a later feature change."""


__all__ = ["register_memory_tools"]

