"""Tool registry for future supervisor-agent tool calling."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


ToolCallable = Callable[..., Awaitable[Any] | Any]


@dataclass(frozen=True)
class RegisteredTool:
    """One named tool callable."""

    name: str
    description: str
    callable: ToolCallable


class ToolRegistry:
    """Small in-process registry for Agent-callable tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, name: str, description: str, tool: ToolCallable) -> None:
        """Register or replace a tool by name."""

        self._tools[name] = RegisteredTool(name=name, description=description, callable=tool)

    def get(self, name: str) -> RegisteredTool | None:
        """Return a registered tool by name."""

        return self._tools.get(name)

    def list_tools(self) -> list[RegisteredTool]:
        """Return registered tools sorted by name."""

        return [self._tools[name] for name in sorted(self._tools)]


__all__ = ["RegisteredTool", "ToolCallable", "ToolRegistry"]

