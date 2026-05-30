"""Workflow-backed tool wrappers for future supervisor agents."""

from argupaper.tools.registry import ToolRegistry


def register_workflow_tools(registry: ToolRegistry) -> None:
    """Register workflow-backed tools.

    The v0.3 architecture refactor creates the extension point only; concrete
    relate/compare/chat tool behavior is implemented by later changes.
    """


__all__ = ["register_workflow_tools"]

