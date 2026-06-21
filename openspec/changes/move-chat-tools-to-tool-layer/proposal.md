## Why

`argupaper chat` currently has working tool implementations under `argupaper.agents.chat.tools`, but that makes the chat runtime the owner of paper/workflow tool behavior. Future Agent features should add tools through the unified `argupaper.tools` layer instead of editing the chat agent internals.

## What Changes

- Move chat paper and workflow tool implementations into `argupaper.tools`.
- Extend the shared tool schemas and registry so tools can carry LangChain `args_schema` metadata and be adapted into `StructuredTool` instances.
- Add a default tool registry/toolbox factory that chat and future agents can reuse.
- Keep chat-specific selected-paper argument injection inside the chat graph.
- Leave `argupaper.agents.chat.tools` as a thin compatibility module only.
- Update README, `docs/SMOKE.md`, and `docs/DONE.md`.

## Capabilities

### New Capabilities

- `unified-agent-tool-layer`: Defines the shared Agent-callable tool layer, LangChain adapter, default registry construction, and chat runtime integration.

### Modified Capabilities

- `langgraph-chat-agent-runtime`: Chat uses the unified tool registry instead of owning tool implementations.

## Impact

- Affected code: `src/argupaper/tools/`, `src/argupaper/agents/chat/graph.py`, `src/argupaper/agents/chat/tools.py`.
- Affected docs: README, `docs/SMOKE.md`, `docs/DONE.md`.
- Public behavior: no intended CLI behavior change; `/papers`, `/use`, `/analyze`, local-library natural-language search, and workflow-backed tools should behave as before.
- Extension impact: new tools should be registered through `argupaper.tools` and automatically become available to chat when added to the default registry.
