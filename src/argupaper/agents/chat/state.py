"""State and data models for the chat agent runtime."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from pydantic import BaseModel, Field


class SelectedPaper(BaseModel):
    """Currently selected paper in one chat process."""

    paper_id: str
    title: str = "Untitled"
    source: str = "N/A"
    library_status: str = "analyzed"


class ChatToolCall(BaseModel):
    """One tool call requested by the ReAct loop."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatObservation(BaseModel):
    """One structured observation returned by a tool."""

    tool: str
    ok: bool = True
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)


class ChatTurnResult(BaseModel):
    """Public result returned to the CLI for one chat turn."""

    response: str
    selected_paper: SelectedPaper | None = None
    warnings: list[str] = Field(default_factory=list)
    interrupted: bool = False
    log_path: str | None = None


class ChatAgentState(TypedDict):
    """LangGraph state for one chat turn.

    The runtime keeps selected paper and messages between turns, while each graph
    invocation appends a new user message and tool observations.
    """

    messages: list[dict[str, str]]
    user_input: str
    session_id: str
    run_id: str
    selected_paper: SelectedPaper | None
    plan: str
    pending_action: dict[str, Any] | None
    tool_calls: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    final_response: str
    warnings: list[str]
    interrupted: bool
    react_steps: int
    max_steps: int
    direct_command: bool
    fallback_reason: str
    memory_context: list[dict[str, Any]]
    agent_roles: list[str]
    handoff_target: str | None
    route: NotRequired[str]
