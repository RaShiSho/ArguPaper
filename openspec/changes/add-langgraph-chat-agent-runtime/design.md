## Context

The project already has reusable workflow boundaries for paper listing, search, and analysis, plus a LangChain adapter around the current OpenAI-compatible `LLMRouter`. The new chat entrypoint must not become a workflow itself: it should be an agent runtime under `argupaper.agents.chat` that orchestrates existing workflows as tools.

## Goals / Non-Goals

**Goals:**

- Implement `argupaper chat` as a LangGraph conversation state graph.
- Keep CLI thin: input, output, progress display, interrupt handling, and exit control only.
- Expose existing workflows as structured tools with no CLI Rich output parsing.
- Support `/papers`, `/use <paper>`, `/analyze`, `/exit`, natural-language search, and selected-paper question answering.
- Provide explicit LLM fallback and warning behavior.
- Persist JSONL audit logs for each chat session without supporting conversation restore.

**Non-Goals:**

- Do not add `workflows/chat` or make chat a fixed workflow.
- Do not implement PaperMemoryIndex in this change.
- Do not implement real multi-agent handoff; only reserve state/tool extension points.
- Do not change `AnalyzeWorkflow`, `ConsensusDetector`, or `ReportGenerator` contracts.

## Decisions

- Use `argupaper.agents.chat` as the module boundary. This keeps the agent runtime near other agent code and avoids overloading `workflows/` with chat orchestration.
- Use LangGraph `StateGraph` with nodes for `planner`, `react`, `tool_executor`, `respond`, and `fallback`. The graph owns state transitions; tools own workflow calls.
- Use JSON action parsing instead of provider-native tool calling. The existing `LLMRouter` works with OpenAI-compatible chat APIs through LangChain Runnables, so JSON actions keep provider requirements minimal.
- Treat slash commands as high-priority user instructions inside the graph except `/exit`, which the CLI handles directly. This preserves a single runtime path for `/papers`, `/use`, and `/analyze`.
- Return structured tool observations and let the CLI format concise summaries. This avoids parsing Rich output and preserves workflow/tool boundaries.
- Add best-effort cancellation by cancelling the active asyncio task. If a lower-level external call cannot stop immediately, the runtime still records interruption and returns control as soon as Python cancellation is observed.

## Risks / Trade-offs

- LangGraph may not be installed in existing environments -> add it to project dependencies and verify imports through compileall/help checks.
- JSON action output may be invalid -> route to fallback, record warnings, and keep slash-command mode available.
- ReAct loops can run too long -> cap each turn at six tool steps by default.
- Workflow failures could obscure chat responses -> tools catch and return structured errors, while the graph records warnings and responds with readable next steps.
- ESC cannot guarantee immediate network aborts -> document best-effort semantics and record interrupted runs in logs.

## Migration Plan

- Add dependencies, config, and `argupaper.agents.chat` modules.
- Register `argupaper chat` without changing existing CLI commands.
- Add docs and smoke scenarios for chat runtime behavior.
- Roll back by removing the command, package, dependencies, and chat config/docs. No persisted user data requires migration because chat state is not restored.

## Open Questions

- None for this change. PaperMemoryIndex and multi-agent specialist handoff are intentionally reserved for later changes.
