"""Tool registry and LangChain adapter for Agent tool calling."""

import inspect
import json
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

    def normalize_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Normalize common LLM-generated argument aliases for one tool."""

        normalized = dict(arguments)
        aliases = _ARGUMENT_ALIASES.get(name, {})
        for alias, target in aliases.items():
            if alias not in normalized:
                continue
            alias_value = normalized.pop(alias)
            if _has_value(normalized.get(target)):
                continue
            normalized[target] = _normalize_alias_value(alias_value)
        return normalized

    def tool_specs(self) -> str:
        """Return schema-aware tool specs for prompts."""

        return "\n\n".join(self._format_tool_spec(tool) for tool in self.list_tools())

    def _format_tool_spec(self, tool: RegisteredTool) -> str:
        lines = [f"- name: {tool.name}", f"  description: {tool.description}"]
        if tool.args_schema is None:
            lines.append("  arguments: none")
            lines.append("  required: none")
            return "\n".join(lines)

        schema = tool.args_schema.model_json_schema()
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines.append("  arguments:")
        for field_name, field_schema in properties.items():
            type_name = _schema_type(field_schema)
            required_text = "required" if field_name in required else "optional"
            description = str(field_schema.get("description", "")).strip()
            default = field_schema.get("default", None)
            suffix_parts = [type_name, required_text]
            if "default" in field_schema and default is not None:
                suffix_parts.append(f"default={json.dumps(default, ensure_ascii=False)}")
            suffix = ", ".join(suffix_parts)
            if description:
                lines.append(f"    - {field_name} ({suffix}): {description}")
            else:
                lines.append(f"    - {field_name} ({suffix})")
        if required:
            lines.append(f"  required: {', '.join(sorted(required))}")
        else:
            lines.append("  required: none")
        return "\n".join(lines)


class LangChainToolbox:
    """Expose a ToolRegistry as LangChain tools with normalized observations."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.tools = self._build_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    async def ainvoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one registered tool and normalize failures as observations."""

        arguments = self.normalize_arguments(name, arguments)
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

    def normalize_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Normalize common LLM-generated argument aliases for one tool."""

        return self.registry.normalize_arguments(name, arguments)

    def tool_specs(self) -> str:
        """Return schema-aware tool specs for prompts."""

        return self.registry.tool_specs()

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


_ARGUMENT_ALIASES: dict[str, dict[str, str]] = {
    "select_paper": {
        "query": "paper",
        "id": "paper",
        "paper_id": "paper",
        "name": "paper",
        "title": "paper",
    },
    "read_paper_context": {
        "id": "paper_id",
        "paper": "paper_id",
        "name": "paper_id",
    },
    "analyze_paper": {
        "id": "paper_id",
        "paper": "paper_id",
        "name": "paper_id",
    },
    "list_papers": {
        "keyword": "query",
        "keywords": "query",
        "name": "query",
    },
    "search_papers": {
        "keyword": "query",
        "keywords": "query",
        "name": "query",
    },
}


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _normalize_alias_value(value: Any) -> Any:
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return value


def _schema_type(field_schema: dict[str, Any]) -> str:
    if "type" in field_schema:
        return str(field_schema["type"])
    any_of = field_schema.get("anyOf")
    if isinstance(any_of, list):
        type_names = [str(item.get("type", "")) for item in any_of if isinstance(item, dict) and item.get("type")]
        if type_names:
            return " | ".join(type_names)
    return "unknown"


__all__ = ["LangChainToolbox", "RegisteredTool", "ToolCallable", "ToolRegistry"]
