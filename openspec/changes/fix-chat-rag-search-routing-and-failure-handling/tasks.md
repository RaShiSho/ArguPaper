## 1. OpenSpec

- [x] 1.1 Create proposal, design, spec, and tasks for chat RAG routing and failure handling.

## 2. Chat Runtime

- [x] 2.1 Make selected-paper injection tool-specific so broad `rag_search_context` calls do not receive `paper_id`.
- [x] 2.2 Add explicit current-paper phrase detection for scoped RAG searches.
- [x] 2.3 Route failed tool observations to final response before another ReAct LLM step can mask the error.
- [x] 2.4 De-duplicate warnings and format failed RAG observations with log path and next-step guidance.

## 3. RAG Vector Store

- [x] 3.1 Add or verify a Milvus scalar index for `paper_id`.
- [x] 3.2 Convert Milvus unsupported-filter failures into clear collection compatibility guidance.
- [x] 3.3 Preserve non-destructive behavior; do not delete or rebuild collections automatically.

## 4. Documentation

- [x] 4.1 Update `docs/SMOKE.md` with broad/scoped RAG chat scenarios and failure behavior.
- [x] 4.2 Update `docs/DONE.md` with a concise implementation note.

## 5. Verification

- [x] 5.1 Run `uv run python -m compileall src/argupaper`.
- [x] 5.2 Run `uv run argupaper chat --help`.
- [x] 5.3 Run focused chat runtime smoke for broad RAG, scoped RAG, and failed RAG observation behavior.
- [x] 5.4 Run `openspec status --change "fix-chat-rag-search-routing-and-failure-handling"`.
