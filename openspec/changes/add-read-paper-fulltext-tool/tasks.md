## 1. OpenSpec

- [x] 1.1 Create proposal, design, spec, and tasks for the fulltext paper tool.

## 2. Tools

- [x] 2.1 Add `ReadPaperFullTextArgs` schema and export it from the tools package.
- [x] 2.2 Implement `read_paper_fulltext` in the PaperStore-backed toolbox.
- [x] 2.3 Register `read_paper_fulltext` in the shared tool registry.
- [x] 2.4 Add argument aliases for `read_paper_fulltext`.

## 3. Chat Runtime

- [x] 3.1 Inject selected paper id into `read_paper_fulltext` tool calls.
- [x] 3.2 Add fulltext observation compaction for responder prompts.
- [x] 3.3 Redact fulltext fields from chat JSONL tool observation logs.
- [x] 3.4 Update ReAct and responder prompts for fulltext behavior.

## 4. Documentation

- [x] 4.1 Update README chat documentation.
- [x] 4.2 Update `docs/SMOKE.md` with fulltext smoke scenarios.
- [x] 4.3 Update `docs/DONE.md`.

## 5. Verification

- [x] 5.1 Run `uv run python -m compileall src/argupaper`.
- [x] 5.2 Run `uv run argupaper chat --help`.
- [x] 5.3 Run direct tool smoke for full, truncated, missing-paper, and include-report cases.
- [x] 5.4 Run fake chat smoke for selected-paper fulltext request and LLM-unavailable fallback.
- [x] 5.5 Verify chat log redaction for `read_paper_fulltext`.
- [x] 5.6 Run `openspec status --change "add-read-paper-fulltext-tool"`.
