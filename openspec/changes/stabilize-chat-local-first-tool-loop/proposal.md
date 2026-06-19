## Why

Recent chat runs show that local paper content requests can be routed to external search first, and malformed tool arguments such as `select_paper({"query": "BackdoorAgent"})` fail validation. The ReAct loop can then repeat the same failing call until the step limit is reached.

This change stabilizes the first-stage chat agent tool loop without adding a new responder. The goal is to make local PaperStore access the default path for local paper questions, expose exact tool schemas to the LLM, normalize common argument aliases before validation, and stop exact duplicate tool calls inside one turn.

## What Changes

- Add a local-first routing guard in `ChatAgentRuntime` before natural-language turns enter LLM planning.
- Expose schema-aware tool specs from the unified `argupaper.tools` registry.
- Normalize common tool argument aliases before invoking LangChain `StructuredTool` validation.
- Detect exact duplicate tool calls by `tool + canonical_json(arguments)` in one graph run.
- Log normalized arguments and duplicate-call blocks.
- Update chat Planner/ReAct prompts with local-first and valid-argument rules.
- Update `docs/SMOKE.md` and `docs/DONE.md`.

## Non-Goals

- Do not add an LLM responder.
- Do not change `_respond()` into content generation from `read_paper_context`.
- Do not add multi-agent handoff.
- Do not change Analyze/Search/PaperStore business logic.

## Impact

- Affected code: `src/argupaper/agents/chat/graph.py`, `src/argupaper/tools/registry.py`, `src/argupaper/prompts/chat_agent/`.
- Affected docs: `docs/SMOKE.md`, `docs/DONE.md`.
- Behavior: local paper content requests should first select/read local PaperStore records; external search remains available for explicit external or new-paper search requests.
