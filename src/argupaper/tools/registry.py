"""Tool registry and LangChain adapter for Agent tool calling."""

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from argupaper.tools.schemas import ToolResult


ToolCallable = Callable[..., Awaitable[Any] | Any]


@dataclass(frozen=True)
class RegisteredTool:
    """One named tool callable."""

    name: str
    description: str
    callable: ToolCallable
    args_schema: type[BaseModel] | None = None


class ToolRegistry:
    """Small in-process registry for Agent-callable tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        tool: ToolCallable,
        *,
        args_schema: type[BaseModel] | None = None,
    ) -> None:
        """Register or replace a tool by name."""

        self._tools[name] = RegisteredTool(
            name=name,
            description=description,
            callable=tool,
            args_schema=args_schema,
        )

    def get(self, name: str) -> RegisteredTool | None:
        """Return a registered tool by name."""

        return self._tools.get(name)

    def list_tools(self) -> list[RegisteredTool]:
        """Return registered tools sorted by name."""

        return [self._tools[name] for name in sorted(self._tools)]


class LangChainToolbox:
    """Expose a ToolRegistry as LangChain tools with normalized observations."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.tools = self._build_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    async def ainvoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one registered tool and normalize failures as observations."""

        tool = self.tools_by_name.get(name)
        if tool is None:
            return {
                "tool": name,
                "ok": False,
                "summary": f"Unknown tool: {name}",
                "data": {"available_tools": sorted(self.tools_by_name)},
                "warnings": [],
            }
        try:
            result = await tool.ainvoke(arguments)
        except Exception as exc:
            return {
                "tool": name,
                "ok": False,
                "summary": f"{name} failed: {exc}",
                "data": {"error_type": type(exc).__name__, "error": str(exc)},
                "warnings": [],
            }
        return self._normalize_result(name, result)

    def descriptions(self) -> str:
        """Return compact tool descriptions for prompts."""

        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in sorted(self.tools, key=lambda item: item.name)
        )

    def _build_tools(self) -> list[StructuredTool]:
        tools: list[StructuredTool] = []
        for item in self.registry.list_tools():
            kwargs: dict[str, Any] = {
                "name": item.name,
                "description": item.description,
                "args_schema": item.args_schema,
            }
            if inspect.iscoroutinefunction(item.callable):
                kwargs["coroutine"] = item.callable
            else:
                kwargs["func"] = item.callable
            tools.append(StructuredTool.from_function(**kwargs))
        return tools

    def _normalize_result(self, tool_name: str, result: Any) -> dict[str, Any]:
        if isinstance(result, ToolResult):
            payload = result.model_dump()
        elif isinstance(result, dict):
            payload = dict(result)
        else:
            payload = {"tool": tool_name, "ok": True, "summary": str(result), "data": {}, "warnings": []}

        payload.setdefault("tool", tool_name)
        payload.setdefault("ok", True)
        payload.setdefault("summary", "")
        payload.setdefault("data", {})
        payload.setdefault("warnings", [])
        if not payload.get("tool"):
            payload["tool"] = tool_name
        if payload.get("data") is None:
            payload["data"] = {}
        if payload.get("warnings") is None:
            payload["warnings"] = []
        return payload


__all__ = ["LangChainToolbox", "RegisteredTool", "ToolCallable", "ToolRegistry"]
