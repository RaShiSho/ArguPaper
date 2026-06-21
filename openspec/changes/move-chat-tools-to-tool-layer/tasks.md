## 1. OpenSpec

- [x] 1.1 Create proposal, design, spec, and tasks for moving chat tools to the unified tool layer.

## 2. Tool Layer

- [x] 2.1 Expand common schemas with `ToolResult` envelope fields and chat tool input schemas.
- [x] 2.2 Extend `ToolRegistry` with `args_schema` and add a LangChain toolbox adapter.
- [x] 2.3 Move PaperStore-backed tools into `argupaper.tools.paper_tools`.
- [x] 2.4 Move workflow-backed tools into `argupaper.tools.workflow_tools`.
- [x] 2.5 Add a default registry/toolbox factory.

## 3. Chat Integration

- [x] 3.1 Switch `ChatAgentRuntime` to build tools from `argupaper.tools`.
- [x] 3.2 Slim `argupaper.agents.chat.tools` to compatibility exports only.

## 4. Documentation and Smoke

- [x] 4.1 Update README with the new tool extension path.
- [x] 4.2 Update `docs/SMOKE.md` with unified tool layer smoke coverage.
- [x] 4.3 Update `docs/DONE.md` with a concise completion note.

## 5. Verification

- [x] 5.1 Run `uv run python -m compileall src/argupaper`.
- [x] 5.2 Run `uv run argupaper chat --help`.
- [x] 5.3 Run local registry smoke checks for `list_papers` and `read_paper_context`.
- [x] 5.4 Run `openspec status --change "move-chat-tools-to-tool-layer"`.
