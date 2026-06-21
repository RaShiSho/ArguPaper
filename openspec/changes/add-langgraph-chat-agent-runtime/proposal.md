## Why

ArguPaper needs an interactive research chat entrypoint that can coordinate existing paper, search, and analyze capabilities without turning chat into another fixed workflow. A LangGraph-backed Agent Runtime gives the CLI a real conversational agent core now, while leaving room for PaperMemoryIndex and future multi-agent research assistants.

## What Changes

- Add `argupaper chat` as an interactive CLI shell with prompt-toolkit input, slash commands, visible task progress, ESC best-effort interruption, and session JSONL logging.
- Add `argupaper.agents.chat` as the home for the chat Agent Runtime: state schema, LangGraph graph builder, planner, ReAct loop, tool executor, and runtime logging.
- Wrap existing `PapersWorkflow`, `AnalyzeWorkflow`, `InteractiveSearchWorkflow`, and PaperStore reads as LangChain tools; chat MUST call these tools instead of reimplementing business logic.
- Add LangGraph as the state-graph engine and keep chat state in memory for each process; no persistent conversation restore is introduced.
- Add chat log configuration under `CHAT_LOG_PATH`, defaulting to `LOG_PATH/chat`.
- Update README, `docs/SMOKE.md`, and `docs/DONE.md`.

## Capabilities

### New Capabilities

- `langgraph-chat-agent-runtime`: Defines the interactive chat command, LangGraph Agent State Graph, workflow-backed tools, fallback behavior, interruption, logging, and future extension points.

### Modified Capabilities

- None.

## Impact

- Affected code: `src/argupaper/agents/chat/`, CLI command registration, configuration loading, tool wrappers, and package dependencies.
- Affected docs: README, `.env.example`, `docs/SMOKE.md`, `docs/DONE.md`, and this OpenSpec change.
- Public CLI impact: adds `argupaper chat`; existing commands remain compatible.
- Dependency impact: adds `langgraph` and `prompt_toolkit`.
- Rollback strategy: remove the chat command registration and `argupaper.agents.chat` package, remove the new dependencies and `CHAT_LOG_PATH` config, and revert docs/OpenSpec updates. Existing PaperStore, cache, search traces, and analyze reports require no migration.
