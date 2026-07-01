## Why

Recent chat runs show that RAG queries can fail in two ways that hide the real cause from the user: broad RAG questions are scoped to the selected paper by default, and tool failures can be replaced by a later ReAct JSON parsing error. This makes the chat agent appear unavailable even when the actual issue is RAG routing or Milvus search.

## What Changes

- Change chat argument preparation so `rag_search_context` does not inherit the selected paper unless the user explicitly scopes the query to the current paper.
- Keep selected-paper injection for paper reading, fulltext, debate, and court tools.
- Route failed tool observations to a deterministic user-facing response instead of continuing into another ReAct LLM step that can mask the tool error.
- Improve RAG failure summaries and warning de-duplication so Milvus errors and RAG log paths remain visible.
- Harden Milvus collection/index handling for `paper_id` scalar filtering and return clear guidance when an existing collection is incompatible.
- Update smoke documentation and done notes.

## Capabilities

### New Capabilities

- `chat-rag-search-routing-and-failure-handling`: Defines correct RAG query scoping, RAG tool failure reporting, and Milvus filter compatibility for chat.

### Modified Capabilities

- `langgraph-chat-agent-runtime`: Chat tool execution must preserve RAG tool errors and must not over-scope broad RAG searches.

## Impact

- Affected code: chat graph argument preparation/failure routing, RAG tool observations, and Milvus vector store collection/index handling.
- Affected systems: local Milvus `paper_chunks` collection and RAG search logs.
- Public behavior: broad chat RAG queries search across indexed papers; current-paper RAG queries remain scoped.
- Rollback: revert the chat routing and Milvus index changes; existing PaperStore data is unaffected.
- Priority: this fixes a broken current chat/RAG path before larger agent expansions such as 4-agent orchestration or knowledge graph features.
