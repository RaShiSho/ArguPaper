## 1. OpenSpec

- [x] 1.1 Create proposal, design, spec, and tasks for chat local-first tool loop stabilization.

## 2. Tool Registry

- [x] 2.1 Add schema-aware tool specs for registered tools.
- [x] 2.2 Add tool argument alias normalization before LangChain validation.

## 3. Chat Runtime

- [x] 3.1 Add local-first natural-language routing for local paper content and local library search requests.
- [x] 3.2 Normalize ReAct tool arguments before execution and logging.
- [x] 3.3 Add exact duplicate tool-call blocking within one turn.
- [x] 3.4 Fix corrupted chat runtime user-facing strings touched by this change.

## 4. Prompts

- [x] 4.1 Update Planner prompt with local-first constraints.
- [x] 4.2 Update ReAct prompt with exact argument schemas, local-first rules, and duplicate-failure rules.
- [x] 4.3 Remove corrupted local-search examples from chat prompts.

## 5. Documentation

- [x] 5.1 Update `docs/SMOKE.md` with local-first tool loop smoke coverage.
- [x] 5.2 Update `docs/DONE.md` with a concise completion note.

## 6. Verification

- [x] 6.1 Run `uv run python -m compileall src/argupaper`.
- [x] 6.2 Run `uv run argupaper chat --help`.
- [x] 6.3 Run prompt formatting and tool normalization smoke checks.
- [x] 6.4 Run `openspec status --change "stabilize-chat-local-first-tool-loop"`.
