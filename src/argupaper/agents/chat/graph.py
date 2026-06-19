"""LangGraph conversation runtime for `argupaper chat`."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Optional
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from argupaper.agents.chat.logging import ChatRuntimeLogger
from argupaper.agents.chat.state import ChatAgentState, ChatTurnResult, SelectedPaper
from argupaper.config import Config
from argupaper.prompts import load_prompt
from argupaper.services.llm import LLMRouter, build_llm_router_runnable, extract_json_object
from argupaper.tools import build_default_toolbox

ProgressCallback = Optional[Callable[[str], None]]

PLANNER_SYSTEM = load_prompt("chat_agent", "planner_system.md")
PLANNER_USER = load_prompt("chat_agent", "planner_user.md")
REACT_SYSTEM = load_prompt("chat_agent", "react_system.md")
REACT_USER = load_prompt("chat_agent", "react_user.md")
RESPOND_SYSTEM = load_prompt("chat_agent", "respond_system.md")


class ChatAgentRuntime:
    """Stateful LangGraph chat agent runtime for one CLI process."""

    def __init__(
        self,
        config: Config,
        *,
        progress_callback: ProgressCallback = None,
        max_steps: int = 6,
    ) -> None:
        self.config = config
        self.progress_callback = progress_callback
        self.max_steps = max_steps
        self.session_id = uuid4().hex[:12]
        self.logger = ChatRuntimeLogger(config.log.chat_path, self.session_id)
        self.llm_router = LLMRouter(config.model)
        self.toolbox = build_default_toolbox(config, progress_callback=progress_callback)
        self.graph = self._build_graph()
        self.messages: list[dict[str, str]] = []
        self.selected_paper: SelectedPaper | None = None
        self.memory_context: list[dict[str, Any]] = []
        self.agent_roles = ["planner", "react_agent"]
        self.handoff_target: str | None = None
        self.logger.write("session_start", {"log_path": str(self.logger.path)})

    async def close(self) -> None:
        """Close runtime resources."""

        await self.llm_router.close()
        self.logger.write("session_end", {})

    async def run_turn(self, user_input: str) -> ChatTurnResult:
        """Run one user turn through the LangGraph agent."""

        run_id = uuid4().hex[:12]
        self.messages.append({"role": "user", "content": user_input})
        state: ChatAgentState = {
            "messages": list(self.messages),
            "user_input": user_input,
            "session_id": self.session_id,
            "run_id": run_id,
            "selected_paper": self.selected_paper,
            "plan": "",
            "pending_action": None,
            "tool_calls": [],
            "observations": [],
            "final_response": "",
            "warnings": [],
            "interrupted": False,
            "react_steps": 0,
            "max_steps": self.max_steps,
            "direct_command": False,
            "fallback_reason": "",
            "memory_context": list(self.memory_context),
            "agent_roles": list(self.agent_roles),
            "handoff_target": self.handoff_target,
            "local_first_goal": None,
        }
        self.logger.write("turn_start", {"run_id": run_id, "input": user_input})
        try:
            result = await self.graph.ainvoke(state)
        except BaseException as exc:
            if type(exc).__name__ == "CancelledError":
                self.logger.write("interrupted", {"run_id": run_id})
                return ChatTurnResult(
                    response="当前任务已中断。",
                    selected_paper=self.selected_paper,
                    interrupted=True,
                    log_path=str(self.logger.path),
                )
            raise

        selected = result.get("selected_paper")
        if isinstance(selected, SelectedPaper):
            self.selected_paper = selected
        elif isinstance(selected, dict):
            self.selected_paper = SelectedPaper(**selected)
        self.messages.append({"role": "assistant", "content": result.get("final_response", "")})
        self.memory_context = list(result.get("memory_context", []))
        self.handoff_target = result.get("handoff_target")
        response = str(result.get("final_response", "")).strip() or "没有生成可用回复。"
        warnings = [str(item) for item in result.get("warnings", []) if str(item).strip()]
        self.logger.write(
            "turn_end",
            {
                "run_id": run_id,
                "response_summary": response[:500],
                "warnings": warnings,
                "selected_paper": self.selected_paper,
            },
        )
        return ChatTurnResult(
            response=response,
            selected_paper=self.selected_paper,
            warnings=warnings,
            interrupted=bool(result.get("interrupted", False)),
            log_path=str(self.logger.path),
        )

    def _build_graph(self):
        graph = StateGraph(ChatAgentState)
        graph.add_node("planner", self._planner)
        graph.add_node("react", self._react)
        graph.add_node("tool_executor", self._tool_executor)
        graph.add_node("respond", self._respond)
        graph.add_node("fallback", self._fallback)
        graph.set_entry_point("planner")
        graph.add_conditional_edges(
            "planner",
            self._route_after_planner,
            {"react": "react", "fallback": "fallback"},
        )
        graph.add_conditional_edges(
            "react",
            self._route_after_react,
            {"tool_executor": "tool_executor", "respond": "respond", "fallback": "fallback"},
        )
        graph.add_edge("tool_executor", "react")
        graph.add_edge("respond", END)
        graph.add_edge("fallback", END)
        return graph.compile()

    async def _planner(self, state: ChatAgentState) -> dict[str, Any]:
        self._progress("Planning next agent step...")
        user_input = state["user_input"].strip()
        self.logger.write("state_transition", {"run_id": state["run_id"], "node": "planner"})
        command_action = self._slash_action(user_input)
        if command_action is not None:
            plan = f"Execute slash command through tool: {command_action.get('tool', 'unknown')}"
            self.logger.write("planner_decision", {"run_id": state["run_id"], "plan": plan, "action": command_action})
            return {
                "plan": plan,
                "pending_action": command_action,
                "direct_command": True,
                "route": "react",
            }

        local_first = self._local_first_action(user_input, state.get("selected_paper"))
        if local_first is not None:
            plan = str(local_first["plan"])
            action = dict(local_first["action"])
            self.logger.write(
                "planner_decision",
                {
                    "run_id": state["run_id"],
                    "plan": plan,
                    "action": action,
                    "local_first": True,
                },
            )
            return {
                "plan": plan,
                "pending_action": action,
                "local_first_goal": local_first["goal"],
                "route": "react",
            }

        if not self.llm_router.has_provider("default"):
            return {
                "fallback_reason": "Default LLM provider is not configured.",
                "route": "fallback",
            }

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PLANNER_SYSTEM),
                ("human", PLANNER_USER),
            ]
        )
        runnable = prompt | build_llm_router_runnable(
            self.llm_router,
            provider_alias="default",
            temperature=0.2,
            max_tokens=500,
        )
        try:
            plan = str(
                await runnable.ainvoke(
                    {
                        "user_input": user_input,
                        "selected_paper": self._selected_text(state.get("selected_paper")),
                        "messages": self._recent_messages(state.get("messages", [])),
                    }
                )
            ).strip()
        except Exception as exc:
            return {
                "fallback_reason": f"Planner LLM failed: {type(exc).__name__}: {exc}",
                "route": "fallback",
            }
        self.logger.write("planner_decision", {"run_id": state["run_id"], "plan": plan})
        return {"plan": plan, "route": "react"}

    async def _react(self, state: ChatAgentState) -> dict[str, Any]:
        self._progress("Running ReAct tool loop...")
        self.logger.write("state_transition", {"run_id": state["run_id"], "node": "react"})
        pending = state.get("pending_action")
        if pending is not None:
            return {"route": "tool_executor"}

        if state.get("direct_command") and state.get("observations"):
            return {
                "final_response": self._format_observation_response(state["observations"][-1]),
                "route": "respond",
            }

        local_first_response = self._continue_or_finish_local_first(state)
        if local_first_response is not None:
            return local_first_response

        if state.get("react_steps", 0) >= state.get("max_steps", self.max_steps):
            return {
                "final_response": "已达到本轮工具调用上限，先根据已有结果收束：\n"
                + self._summarize_observations(state.get("observations", [])),
                "warnings": [*state.get("warnings", []), "ReAct loop reached the step limit."],
                "route": "respond",
            }

        if not self.llm_router.has_provider("default"):
            return {
                "fallback_reason": "Default LLM provider is not configured.",
                "route": "fallback",
            }

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REACT_SYSTEM),
                ("human", REACT_USER),
            ]
        )
        runnable = prompt | build_llm_router_runnable(
            self.llm_router,
            provider_alias="default",
            temperature=0.2,
            max_tokens=900,
        )
        try:
            response = str(
                await runnable.ainvoke(
                    {
                        "tools": self.toolbox.tool_specs(),
                        "plan": state.get("plan", ""),
                        "user_input": state["user_input"],
                        "selected_paper": self._selected_text(state.get("selected_paper")),
                        "observations": self._summarize_observations(state.get("observations", [])),
                        "messages": self._recent_messages(state.get("messages", [])),
                    }
                )
            )
            action = extract_json_object(response)
        except Exception as exc:
            return {
                "fallback_reason": f"ReAct LLM returned invalid action: {type(exc).__name__}: {exc}",
                "route": "fallback",
            }

        action_name = str(action.get("action", "")).strip()
        if action_name == "tool_call":
            tool_name = str(action.get("tool", "")).strip()
            raw_arguments = action.get("arguments", {}) or {}
            arguments = self._prepare_tool_arguments(
                tool_name,
                dict(raw_arguments) if isinstance(raw_arguments, dict) else {},
                state.get("selected_paper"),
            )
            self.logger.write(
                "react_decision",
                {
                    "run_id": state["run_id"],
                    "action": action,
                    "normalized_arguments": arguments,
                },
            )
            duplicate = self._find_duplicate_tool_call(state.get("tool_calls", []), tool_name, arguments)
            if duplicate is not None:
                signature = self._tool_signature(tool_name, arguments)
                self.logger.write(
                    "duplicate_tool_call_blocked",
                    {
                        "run_id": state["run_id"],
                        "tool": tool_name,
                        "arguments": arguments,
                        "signature": signature,
                        "previous_ok": duplicate.get("ok", False),
                    },
                )
                warnings = list(state.get("warnings", []))
                warning = f"Duplicate tool call blocked: {tool_name}"
                if warning not in warnings:
                    warnings.append(warning)
                if duplicate.get("ok", False) and state.get("observations"):
                    final_response = self._format_observation_response(state["observations"][-1])
                else:
                    final_response = (
                        f"工具调用 `{tool_name}` 使用相同参数重复失败，已停止重复执行。"
                        + ("\n" + self._summarize_observations(state.get("observations", [])))
                    )
                return {
                    "final_response": final_response,
                    "warnings": warnings,
                    "route": "respond",
                }
            return {
                "pending_action": {
                    "action": "tool_call",
                    "tool": tool_name,
                    "arguments": arguments,
                },
                "react_steps": state.get("react_steps", 0) + 1,
                "route": "tool_executor",
            }
        self.logger.write("react_decision", {"run_id": state["run_id"], "action": action})
        if action_name in {"final_answer", "ask_user"}:
            return {"final_response": str(action.get("content", "")).strip(), "route": "respond"}
        return {
            "fallback_reason": f"Unsupported ReAct action: {action_name or 'empty'}",
            "route": "fallback",
        }

    async def _tool_executor(self, state: ChatAgentState) -> dict[str, Any]:
        self._progress("Executing workflow-backed tool...")
        self.logger.write("state_transition", {"run_id": state["run_id"], "node": "tool_executor"})
        action = state.get("pending_action") or {}
        tool_name = str(action.get("tool", "")).strip()
        raw_arguments = dict(action.get("arguments", {}) or {})
        arguments = self._prepare_tool_arguments(tool_name, raw_arguments, state.get("selected_paper"))
        signature = self._tool_signature(tool_name, arguments)
        self.logger.write(
            "tool_call",
            {
                "run_id": state["run_id"],
                "tool": tool_name,
                "arguments": arguments,
                "raw_arguments": raw_arguments,
                "signature": signature,
            },
        )
        observation = await self.toolbox.ainvoke(tool_name, arguments)
        self.logger.write(
            "tool_observation",
            {"run_id": state["run_id"], "tool": tool_name, "observation": observation},
        )
        observations = [*state.get("observations", []), observation]
        tool_calls = [
            *state.get("tool_calls", []),
            {
                "tool": tool_name,
                "arguments": arguments,
                "ok": observation.get("ok", False),
                "signature": signature,
            },
        ]
        update: dict[str, Any] = {
            "pending_action": None,
            "observations": observations,
            "tool_calls": tool_calls,
        }
        selected_payload = observation.get("data", {}).get("selected_paper")
        if selected_payload:
            update["selected_paper"] = SelectedPaper(**selected_payload)
        warnings = list(state.get("warnings", []))
        for warning in observation.get("data", {}).get("warnings", []) or []:
            if warning not in warnings:
                warnings.append(str(warning))
        if not observation.get("ok", False):
            warnings.append(str(observation.get("summary", "Tool failed.")))
        update["warnings"] = warnings
        return update

    async def _respond(self, state: ChatAgentState) -> dict[str, Any]:
        self._progress("Preparing response...")
        self.logger.write("state_transition", {"run_id": state["run_id"], "node": "respond"})
        final_response = str(state.get("final_response", "")).strip()
        if final_response:
            return {"final_response": final_response}
        if state.get("observations"):
            return {"final_response": self._format_observation_response(state["observations"][-1])}
        return {"final_response": "没有可用结果。"}

    async def _fallback(self, state: ChatAgentState) -> dict[str, Any]:
        reason = str(state.get("fallback_reason", "")).strip() or "Agent runtime could not continue."
        self.logger.write("fallback", {"run_id": state["run_id"], "reason": reason})
        command_help = "LLM 自然语言 Agent 当前不可用。仍可使用：/papers、/use <paper-id-or-name>、/analyze、/exit。"
        return {
            "final_response": f"{command_help}\n\n原因：{reason}",
            "warnings": [*state.get("warnings", []), reason],
        }

    def _route_after_planner(self, state: ChatAgentState) -> str:
        return state.get("route", "react")

    def _route_after_react(self, state: ChatAgentState) -> str:
        return state.get("route", "respond")

    def _slash_action(self, user_input: str) -> dict[str, Any] | None:
        if not user_input.startswith("/"):
            return None
        command, _, rest = user_input.partition(" ")
        normalized = command.strip().lower()
        argument = rest.strip()
        if normalized == "/papers":
            return {"action": "tool_call", "tool": "list_papers", "arguments": {"limit": 20}}
        if normalized == "/use":
            if not argument:
                return {"action": "tool_call", "tool": "select_paper", "arguments": {"paper": ""}}
            return {"action": "tool_call", "tool": "select_paper", "arguments": {"paper": argument}}
        if normalized == "/analyze":
            return {"action": "tool_call", "tool": "analyze_paper", "arguments": {"rounds": 3}}
        return {
            "action": "tool_call",
            "tool": "unknown_slash_command",
            "arguments": {"command": normalized},
        }

    def _format_observation_response(self, observation: dict[str, Any]) -> str:
        summary = str(observation.get("summary", "")).strip()
        data = observation.get("data", {})
        tool = observation.get("tool")
        if tool == "list_papers" and data.get("records"):
            return summary
        if tool == "search_papers" and data.get("results"):
            lines = [summary]
            for index, item in enumerate(data["results"][:5], start=1):
                lines.append(
                    f"{index}. {item.get('title', 'Untitled')} "
                    f"({item.get('year', 'N/A')}, {item.get('source', 'unknown')})"
                )
            return "\n".join(lines)
        return summary or "工具执行完成。"

    def _summarize_observations(self, observations: list[dict[str, Any]]) -> str:
        if not observations:
            return "No observations yet."
        return "\n".join(
            f"- {item.get('tool', 'tool')}: {item.get('summary', '')}" for item in observations[-6:]
        )

    def _selected_text(self, selected: Any) -> str:
        selected_dict = self._selected_dict(selected)
        if not selected_dict:
            return "None"
        return (
            f"{selected_dict.get('paper_id')} | {selected_dict.get('title')} | "
            f"{selected_dict.get('library_status')}"
        )

    def _selected_dict(self, selected: Any) -> dict[str, Any] | None:
        if selected is None:
            return None
        if isinstance(selected, SelectedPaper):
            return selected.model_dump()
        if isinstance(selected, dict):
            return selected
        return None

    def _recent_messages(self, messages: list[dict[str, str]]) -> str:
        recent = messages[-8:]
        return "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in recent)

    def _progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)

    def _local_first_action(self, user_input: str, selected: Any) -> dict[str, Any] | None:
        if self._is_explicit_external_search(user_input):
            return None
        if self._is_local_library_search(user_input):
            query = self._extract_local_library_query(user_input)
            arguments: dict[str, Any] = {"limit": self._extract_limit(user_input, default=20)}
            if query:
                arguments["query"] = query
            return {
                "goal": "list_local",
                "plan": "Local-first: search saved PaperStore records before any external search.",
                "action": {"action": "tool_call", "tool": "list_papers", "arguments": arguments},
            }
        if not self._is_paper_content_request(user_input):
            return None
        if self._mentions_current_paper(user_input) and self._selected_dict(selected):
            return {
                "goal": "read_selected",
                "plan": "Local-first: read the selected PaperStore record context.",
                "action": {"action": "tool_call", "tool": "read_paper_context", "arguments": {}},
            }
        paper_query = self._extract_local_paper_query(user_input)
        if paper_query:
            return {
                "goal": "read_context_after_select",
                "plan": "Local-first: select a matching saved PaperStore record before considering external search.",
                "action": {
                    "action": "tool_call",
                    "tool": "select_paper",
                    "arguments": {"paper": paper_query},
                },
            }
        if self._selected_dict(selected):
            return {
                "goal": "read_selected",
                "plan": "Local-first: read the selected PaperStore record context.",
                "action": {"action": "tool_call", "tool": "read_paper_context", "arguments": {}},
            }
        return None

    def _continue_or_finish_local_first(self, state: ChatAgentState) -> dict[str, Any] | None:
        goal = state.get("local_first_goal")
        observations = state.get("observations", [])
        if not goal or not observations:
            return None

        last = observations[-1]
        last_tool = str(last.get("tool", ""))
        if goal == "list_local":
            return {"final_response": self._format_observation_response(last), "route": "respond"}
        if goal == "read_selected" and last_tool == "read_paper_context":
            return {"final_response": self._format_observation_response(last), "route": "respond"}
        if goal == "read_context_after_select":
            if last_tool == "read_paper_context":
                return {"final_response": self._format_observation_response(last), "route": "respond"}
            if last_tool == "select_paper" and last.get("ok", False):
                return {
                    "pending_action": {
                        "action": "tool_call",
                        "tool": "read_paper_context",
                        "arguments": {},
                    },
                    "route": "tool_executor",
                }
        return None

    def _prepare_tool_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        selected: Any,
    ) -> dict[str, Any]:
        normalized = self.toolbox.normalize_arguments(tool_name, arguments)
        return default_paper_id(tool_name, normalized, self._selected_dict(selected))

    def _find_duplicate_tool_call(
        self,
        tool_calls: list[dict[str, Any]],
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | None:
        signature = self._tool_signature(tool_name, arguments)
        for item in reversed(tool_calls):
            item_signature = str(item.get("signature", ""))
            if not item_signature:
                item_signature = self._tool_signature(
                    str(item.get("tool", "")),
                    dict(item.get("arguments", {}) or {}),
                )
            if item_signature == signature:
                return item
        return None

    def _tool_signature(self, tool_name: str, arguments: dict[str, Any]) -> str:
        payload = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return f"{tool_name}:{payload}"

    def _is_explicit_external_search(self, user_input: str) -> bool:
        text = user_input.lower()
        if "本地" in text or "本地库" in text or "论文库" in text:
            return False
        markers = [
            "外部",
            "全网",
            "联网",
            "网上",
            "新论文",
            "最新",
            "推荐",
            "arxiv",
            "semantic scholar",
            "google scholar",
            "serpapi",
        ]
        return any(marker in text for marker in markers)

    def _is_local_library_search(self, user_input: str) -> bool:
        text = user_input.lower()
        has_local_scope = any(marker in text for marker in ("本地论文库", "本地库", "本地", "paperstore"))
        has_search_verb = any(marker in text for marker in ("找", "查找", "搜索", "检索", "筛选", "filter", "search"))
        return has_local_scope and has_search_verb

    def _is_paper_content_request(self, user_input: str) -> bool:
        text = user_input.lower()
        markers = [
            "讲讲",
            "看看",
            "介绍",
            "相关信息",
            "具体内容",
            "讲了什么",
            "说了什么",
            "这篇论文",
            "这篇文章",
            "当前论文",
            "selected paper",
            "tell me about",
            "summarize",
        ]
        return any(marker in text for marker in markers)

    def _mentions_current_paper(self, user_input: str) -> bool:
        text = user_input.lower()
        return any(marker in text for marker in ("这篇", "这篇论文", "这篇文章", "当前论文", "selected paper"))

    def _extract_limit(self, user_input: str, *, default: int) -> int:
        match = re.search(r"(\d{1,2})\s*(?:篇|个|papers?|条)?", user_input, flags=re.IGNORECASE)
        if match is None:
            return default
        return max(1, min(int(match.group(1)), 50))

    def _extract_local_library_query(self, user_input: str) -> str | None:
        for pattern in (r"与\s*(?P<query>.+?)\s*相关", r"关于\s*(?P<query>.+?)\s*的"):
            match = re.search(pattern, user_input, flags=re.IGNORECASE)
            if match:
                return self._clean_extracted_query(match.group("query"))
        cleaned = re.sub(r"\d+\s*(?:篇|个|papers?|条)?", " ", user_input, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"(在|从|本地论文库|本地库|本地|论文库|中|里|找|查找|搜索|检索|筛选|论文|文章|相关|有关|给我|帮我)",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        return self._clean_extracted_query(cleaned)

    def _extract_local_paper_query(self, user_input: str) -> str | None:
        patterns = [
            r"(?:帮我看看|和我讲讲|讲讲|看看|介绍一下|介绍|说说|聊聊|解释一下|解释|阅读)\s*(?P<paper>.+?)(?:这篇论文|这篇文章|这篇|论文|文章|的具体内容|具体内容|讲了什么|说了什么|内容|相关信息|$)",
            r"(?P<paper>[A-Za-z0-9][A-Za-z0-9_.:\- ]{1,80})\s*(?:这篇论文|这篇文章|这篇|论文|文章|paper)",
        ]
        for pattern in patterns:
            match = re.search(pattern, user_input, flags=re.IGNORECASE)
            if match:
                return self._clean_extracted_query(match.group("paper"))
        return None

    def _clean_extracted_query(self, value: str) -> str | None:
        cleaned = value.strip(" \t\r\n，。！？!?：:；;、\"'`")
        cleaned = re.sub(r"^(帮我|给我|和我|请|一下|这篇|这篇论文|这篇文章)\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return None
        return cleaned


def default_paper_id(
    tool_name: str,
    arguments: dict[str, Any],
    selected_paper: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fill paper_id from the selected paper when a tool omitted it."""

    if tool_name not in {"read_paper_context", "analyze_paper"}:
        return arguments
    if arguments.get("paper_id") or selected_paper is None:
        return arguments
    filled = dict(arguments)
    filled["paper_id"] = selected_paper.get("paper_id")
    return filled
