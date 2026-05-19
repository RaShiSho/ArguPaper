## Why

`argupaper analyze` already has a 2-agent debate stage, but Support/Skeptic reasoning and debate orchestration are still implemented as project-specific classes with hard-coded text generation. Moving the analyze debate stage onto LangChain LCEL and prompt templates improves maintainability, makes future agent prompt iteration explicit, and stabilizes the current core report path before adding broader 4-agent or knowledge-graph capabilities.

This is higher priority than expanding agent count because the current report quality depends directly on the existing Support/Skeptic debate; making that path easier to inspect, prompt, and downgrade safely improves the main workflow users already run.

## What Changes

- Add an internal LangChain adapter that reuses the existing `LLMRouter` and OpenAI-compatible provider configuration without adding `langchain-openai`, OpenAI SDK, or new environment variables.
- Refactor Support/Skeptic analyze agents so their public `think(context) -> str` contract remains compatible while their primary implementation uses LangChain `ChatPromptTemplate` and LCEL Runnable composition.
- Preserve the existing rule-based Support/Skeptic output as role-level fallback for missing LLM provider, provider failure, or empty model output.
- Refactor `DebateChain` to keep the current round order, early-stop behavior, and `DebateState`/`AgentMessage` output shape while collecting downgrade warnings for AnalyzeWorkflow.
- Keep Search Agent and SearchAgentWorkflow outside this change.
- Update README, `docs/SMOKE.md`, and `docs/DONE.md` to document LangChain-backed analyze debate and manual fallback verification.

## Capabilities

### New Capabilities

- `langchain-analyze-agent-orchestration`: Defines LangChain-backed Support/Skeptic debate behavior, fallback handling, output compatibility, and Search Agent non-impact for the analyze workflow.

### Modified Capabilities

- None.

## Impact

- Affected code: `AnalyzeWorkflow`, Support/Skeptic agent classes, `DebateChain`, `LLMRouter` integration surface, and debate state models.
- Affected docs: README, `docs/SMOKE.md`, and `docs/DONE.md`.
- Public CLI/API impact: no breaking command or web API changes; analyze output gains warning visibility when LangChain/LLM debate falls back.
- Dependency impact: no new runtime dependency or provider configuration; existing LangChain packages and existing LLM provider env vars are reused.
- Rollback strategy: remove the LangChain adapter and debate prompt wiring, restore Support/Skeptic to direct rule-based `think()` implementations, and restore `DebateChain` to direct self-managed agent calls. Existing cache files, reports, PaperStore records, and search traces require no migration or cleanup.
