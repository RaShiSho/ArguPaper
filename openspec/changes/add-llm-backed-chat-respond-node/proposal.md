## Why

The chat runtime can already call tools such as `read_paper_context`, but the final `respond` node only returns an existing `final_response` or the last tool observation summary. This causes successful context reads to produce responses like `Loaded context...` instead of explaining the paper, and ReAct JSON failures can discard useful observations.

## What Changes

- Upgrade the chat `respond` node into an LLM-backed summarizer when observations are available and no final response has already been produced.
- Keep slash command output deterministic by preserving existing `final_response` short-circuit behavior.
- Route ReAct invalid-action failures with useful observations to `respond` instead of immediate fallback.
- Expand chat responder prompts so paper context, analyze reports, search results, and local paper lists are summarized without inventing details.
- Add responder audit log events and update README, `docs/SMOKE.md`, and `docs/DONE.md`.

## Capabilities

### New Capabilities

- `llm-backed-chat-respond-node`: Defines observation-grounded LLM response generation for chat.

### Modified Capabilities

- `langgraph-chat-agent-runtime`: The final response node can now synthesize tool observations into user-facing answers.

## Impact

- Affected code: `src/argupaper/agents/chat/graph.py` and chat prompts.
- Affected docs: README, `docs/SMOKE.md`, `docs/DONE.md`.
- Public behavior: natural-language paper content requests should return an explanation based on `read_paper_context`, not just a tool summary.
- Compatibility: no changes to tools, workflows, CLI commands, or environment variables.
