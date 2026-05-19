## Context

Analyze currently runs structure extraction, evidence checks, 2-agent debate, consensus detection, and report generation in one workflow. The debate step already returns `DebateState` and `AgentMessage`, but Support/Skeptic text is produced by hand-written classes rather than explicit LangChain prompts and runnable composition.

The project already depends on LangChain and has an OpenAI-compatible `LLMRouter`. This change should reuse those pieces instead of adding provider dependencies. The Search Agent is already functional and remains out of scope.

## Goals / Non-Goals

**Goals:**

- Make analyze Support/Skeptic debate use LangChain `ChatPromptTemplate` and LCEL Runnable composition.
- Keep `DebateChain.run(context) -> DebateState` and the existing report payload compatible.
- Preserve current round order, early-stop behavior, and fallback debate reliability.
- Surface LLM/LangChain downgrade reasons as workflow warnings.

**Non-Goals:**

- Do not migrate Search Agent parsing or retrieval orchestration.
- Do not add LangGraph, `langchain-openai`, OpenAI SDK, or new provider environment variables.
- Do not change ConsensusDetector or ReportGenerator input contracts.
- Do not introduce pytest, ruff, or mypy automation.

## Decisions

- Use a small internal `LLMRouter` LCEL adapter rather than a standard provider package. This keeps current OpenAI-compatible provider configuration as the single source of truth and avoids new dependencies.
- Keep `AgentBase.think(context) -> str` as the compatibility seam. Support/Skeptic agents can be LangChain-backed internally while `DebateChain` and smoke snippets remain easy to reason about.
- Put role prompts in code for this first refactor, close to the role classes, because the immediate goal is orchestration structure rather than external prompt management. A future change can move prompts to files once iteration volume justifies it.
- Add warnings to `DebateState` instead of changing `AgentMessage`. AnalyzeWorkflow can merge these warnings before judge/report generation while ConsensusDetector and ReportGenerator continue to consume existing message shapes.
- Keep fallback generation role-local. If the default LLM provider is missing, fails, or returns empty content, Support/Skeptic return the current deterministic fallback content and record a warning.

## Risks / Trade-offs

- LangChain API surface can differ between installed versions -> use only stable `langchain_core.prompts` and `langchain_core.runnables` primitives already available in the environment.
- LLM output may be verbose or weakly grounded -> prompts must constrain output to concise evidence-aware debate statements and fallback remains available.
- Warning propagation could be lost if only agent-local state is used -> `DebateChain` must collect each role's latest warnings into `DebateState.warnings`, and AnalyzeWorkflow must merge them into final warnings.
- Refactor could accidentally change report structure -> keep `DebateState.messages`, `support_positions`, `skeptic_positions`, and `consensus_reached` semantics unchanged.

## Migration Plan

- Add LangChain adapter and role prompt plumbing behind existing public interfaces.
- Update AnalyzeWorkflow to provide an `LLMRouter` to `DebateChain` and close it after the run.
- Update smoke docs for LangChain success and fallback paths.
- Rollback by deleting the adapter and prompt wiring, restoring Support/Skeptic to direct rule-based `think()` implementations, and removing `DebateState.warnings` merge behavior.

## Open Questions

- None for this change. Search Agent and prompt file extraction are intentionally deferred to later changes.
