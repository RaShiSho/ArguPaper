## 1. OpenSpec and Dependencies

- [x] 1.1 Create OpenSpec proposal, design, spec, and tasks for the LangGraph chat agent runtime.
- [x] 1.2 Add `langgraph` and `prompt_toolkit` dependencies and refresh the lockfile.

## 2. Agent Runtime

- [x] 2.1 Add `argupaper.agents.chat` state, action, and observation models.
- [x] 2.2 Implement workflow-backed LangChain tool wrappers for papers, selected paper context, analyze, and search.
- [x] 2.3 Implement the LangGraph planner, ReAct loop, tool executor, respond, and fallback nodes.
- [x] 2.4 Add JSONL runtime logging for session events, state transitions, tool calls, warnings, final responses, and interruptions.

## 3. CLI Integration

- [x] 3.1 Add `argupaper chat` command with prompt-toolkit interactive input and Rich output.
- [x] 3.2 Support `/papers`, `/use <paper>`, `/analyze`, `/exit`, natural-language routing, task progress output, and ESC best-effort cancellation.
- [x] 3.3 Add `CHAT_LOG_PATH` configuration with default `LOG_PATH/chat`.

## 4. Documentation and Smoke

- [x] 4.1 Update README with chat runtime usage, dependencies, commands, fallback, logs, and extension boundaries.
- [x] 4.2 Update `docs/SMOKE.md` with chat manual acceptance scenarios.
- [x] 4.3 Update `docs/DONE.md` with a concise completion note.

## 5. Verification

- [x] 5.1 Run `uv lock`.
- [x] 5.2 Run `uv run python -m compileall src/argupaper`.
- [x] 5.3 Run `uv run argupaper --help` and `uv run argupaper chat --help`.
- [x] 5.4 Run `openspec status --change "add-langgraph-chat-agent-runtime"`.
