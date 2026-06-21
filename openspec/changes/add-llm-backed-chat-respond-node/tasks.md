## 1. OpenSpec

- [x] 1.1 Create proposal, design, spec, and tasks for the LLM-backed respond node.

## 2. Runtime

- [x] 2.1 Add LLM-backed response generation in `ChatAgentRuntime._respond()`.
- [x] 2.2 Route ReAct invalid JSON with successful observations to `respond`.
- [x] 2.3 Adjust local-first paper context completion so `respond` can explain context.
- [x] 2.4 Add compact observation formatting for responder prompts.
- [x] 2.5 Add responder LLM call/failure/fallback audit logs.

## 3. Prompts and Documentation

- [x] 3.1 Expand responder prompts for observation-grounded paper/content/search summaries.
- [x] 3.2 Update README chat behavior notes.
- [x] 3.3 Update `docs/SMOKE.md` with responder smoke scenarios.
- [x] 3.4 Update `docs/DONE.md`.

## 4. Verification

- [x] 4.1 Run `uv run python -m compileall src/argupaper`.
- [x] 4.2 Run `uv run argupaper chat --help`.
- [x] 4.3 Run fake-LLM runtime smoke for `read_paper_context -> respond`.
- [x] 4.4 Run responder fallback smoke with unavailable LLM.
- [x] 4.5 Run `openspec status --change "add-llm-backed-chat-respond-node"`.
