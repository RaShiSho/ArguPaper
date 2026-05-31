"""LangGraph conversation runtime for `argupaper chat`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from argupaper.agents.chat.logging import ChatRuntimeLogger
from argupaper.agents.chat.state import ChatAgentState, ChatTurnResult, SelectedPaper
from argupaper.agents.chat.tools import ChatToolbox, default_paper_id
from argupaper.config import Config
from argupaper.services.llm import LLMRouter, build_llm_router_runnable, extract_json_object

ProgressCallback = Optional[Callable[[str], None]]

PLANNER_SYSTEM = """You are ArguPaper's research chat planner.
Plan one short next-step strategy for a research assistant turn.
You must rely on the registered tools for paper search, PaperStore access, and analysis.
Do not claim to have run a workflow unless a tool observation says it ran.
Keep the plan concise."""

REACT_SYSTEM = """You are ArguPaper's ReAct research assistant.
You can only act through these tools:
{tools}

Return exactly one JSON object, with one of these shapes:
{"action":"tool_call","tool":"tool_name","arguments":{...}}
{"action":"final_answer","content":"answer for the user"}
{"action":"ask_user","content":"short clarification question"}

Rules:
- Use list_papers for listing the local library.
- Use select_paper before answering about an unspecified paper.
- Use read_paper_context before answering questions about the selected paper unless the needed context is already in observations.
- Use analyze_paper for analysis requests.
- Use search_papers for external paper search requests.
- Never invent tool results."""

RESPOND_SYSTEM = """You are ArguPaper's concise CLI chat responder.
Answer the user from the available plan and observations.
Mention warnings or tool errors briefly when relevant.
Do not invent paper details beyond the provided observations."""


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
        self.toolbox = ChatToolbox(config, progress_callback)
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

        if not self.llm_router.has_provider("default"):
            return {
                "fallback_reason": "Default LLM provider is not configured.",
                "route": "fallback",
            }

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PLANNER_SYSTEM),
                (
                    "human",
                    "User input:\n{user_input}\n\nSelected paper:\n{selected_paper}\n\nRecent messages:\n{messages}",
                ),
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
                (
                    "human",
                    "Plan:\n{plan}\n\nUser input:\n{user_input}\n\nSelected paper:\n{selected_paper}\n\n"
                    "Observations:\n{observations}\n\nRecent messages:\n{messages}",
                ),
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
                        "tools": self.toolbox.descriptions(),
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

        self.logger.write("react_decision", {"run_id": state["run_id"], "action": action})
        action_name = str(action.get("action", "")).strip()
        if action_name == "tool_call":
            return {
                "pending_action": {
                    "action": "tool_call",
                    "tool": str(action.get("tool", "")).strip(),
                    "arguments": action.get("arguments", {}) or {},
                },
                "react_steps": state.get("react_steps", 0) + 1,
                "route": "tool_executor",
            }
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
        arguments = dict(action.get("arguments", {}) or {})
        arguments = default_paper_id(arguments, self._selected_dict(state.get("selected_paper")))
        self.logger.write(
            "tool_call",
            {"run_id": state["run_id"], "tool": tool_name, "arguments": arguments},
        )
        observation = await self.toolbox.ainvoke(tool_name, arguments)
        self.logger.write(
            "tool_observation",
            {"run_id": state["run_id"], "tool": tool_name, "observation": observation},
        )
        observations = [*state.get("observations", []), observation]
        tool_calls = [
            *state.get("tool_calls", []),
            {"tool": tool_name, "arguments": arguments, "ok": observation.get("ok", False)},
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
