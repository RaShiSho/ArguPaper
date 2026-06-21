## 1. LangChain Adapter

- [x] 1.1 Add an internal LCEL adapter that reuses `LLMRouter` and accepts LangChain prompt output; verifiable by invoking it with a fake router/client.
- [x] 1.2 Ensure the adapter uses the default provider alias and requires no new dependency or environment variable.

## 2. Debate Role Refactor

- [x] 2.1 Refactor SupportAgent to use a LangChain prompt/runnable path before falling back to deterministic support text; verifiable by fake LLM output.
- [x] 2.2 Refactor SkepticAgent to use a LangChain prompt/runnable path before falling back to deterministic skeptic text; verifiable by fake LLM output.
- [x] 2.3 Preserve role-local fallback behavior for missing provider, provider failure, and empty output, with warning details available to the debate chain.

## 3. Debate and Analyze Integration

- [x] 3.1 Update DebateChain to inject the shared router, preserve round order and early-stop behavior, and collect role fallback warnings into DebateState.
- [x] 3.2 Update AnalyzeWorkflow to create/close the debate LLM router and merge debate warnings into final analyze warnings before report generation.
- [x] 3.3 Confirm SearchAgentWorkflow remains unchanged and does not depend on the new analyze debate adapter.

## 4. Documentation and Smoke

- [x] 4.1 Update README to describe LangChain-backed analyze debate and fallback behavior.
- [x] 4.2 Update `docs/SMOKE.md` with LangChain debate success and fallback verification snippets.
- [x] 4.3 Update `docs/DONE.md` with a concise completion note.

## 5. Verification

- [x] 5.1 Run `uv run python -m compileall src/argupaper`.
- [x] 5.2 Run `uv run argupaper analyze --help`.
- [x] 5.3 Run manual fake-router smoke snippets for LangChain success and fallback behavior.
- [x] 5.4 Run `openspec status --change "langchain-analyze-agent-orchestration"` and confirm artifacts are complete.
