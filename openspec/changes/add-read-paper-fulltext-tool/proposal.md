## Why

The chat runtime can read lightweight paper context through `read_paper_context`, but that tool intentionally returns excerpts. Users sometimes need the Agent to inspect the full local `paper.md` content for detailed explanation or full-text-oriented tasks. The full markdown already exists in PaperStore, so the missing capability is an Agent-callable tool with safe response and logging behavior.

## What Changes

- Add a `read_paper_fulltext` tool in the shared `argupaper.tools` layer.
- Keep `read_paper_context` unchanged as the lightweight context tool.
- Allow chat to inject the selected paper id into `read_paper_fulltext`.
- Teach ReAct prompts when to prefer fulltext over lightweight context.
- Make `respond` understand fulltext observations while avoiding direct full-text dumps in CLI responses.
- Redact fulltext fields from chat JSONL logs and store only metadata such as path, length, hash, and truncation status.
- Update README, `docs/SMOKE.md`, and `docs/DONE.md`.

## Capabilities

### New Capabilities

- `read-paper-fulltext-tool`: Defines full local markdown reading for Agent use.

### Modified Capabilities

- `langgraph-chat-agent-runtime`: Chat can select and use the fulltext tool, summarize it through `respond`, and redact fulltext observations in logs.

## Impact

- Affected code: shared tools, chat graph runtime, chat prompts.
- Affected docs: README, `docs/SMOKE.md`, `docs/DONE.md`.
- Public behavior: natural-language requests for full paper text or detailed full-paper explanation can use local `paper.md`; CLI should not print the entire paper by default.
- Compatibility: no change to existing workflow behavior or `read_paper_context` output.
