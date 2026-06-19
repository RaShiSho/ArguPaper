## Context

`ChatAgentRuntime` already separates tool execution from final response generation in the graph, but `_respond()` is currently deterministic formatting only. The existing `RESPOND_SYSTEM` prompt is loaded but unused for LLM calls. Recent chat logs show successful `read_paper_context` observations being returned as raw summaries.

## Goals / Non-Goals

**Goals:**

- Let `respond` use the default LLM provider to summarize observations when useful.
- Preserve deterministic slash-command responses.
- Recover from ReAct invalid JSON when useful observations already exist.
- Keep no-LLM behavior safe by falling back to existing observation formatting.

**Non-Goals:**

- Do not add a new provider configuration.
- Do not introduce multi-agent handoff.
- Do not alter PaperStore, tools, or workflow business logic.

## Decisions

- `respond` remains the graph terminal node; it calls the LLM only when `final_response` is empty and observations exist.
- Direct slash commands continue to produce `final_response` before `respond`, so `/papers`, `/use`, and `/analyze` remain deterministic by default.
- Local-first paper content requests stop pre-filling `final_response` after `read_paper_context`; this lets `respond` explain the paper.
- Observation payloads are compacted before being passed to the responder to avoid sending unbounded tool output.
- If responder LLM is missing, fails, or returns empty output, `_respond()` logs the fallback and returns the existing deterministic observation summary.

## Risks / Trade-offs

- LLM responses can still be unavailable when the provider network fails. The fallback preserves usable but lower-quality output.
- Passing paper excerpts to the responder increases token usage. Compacting observations bounds the prompt.
- The responder may summarize imperfectly; prompts must explicitly prohibit inventing details outside observations.
