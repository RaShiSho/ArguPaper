## Context

`ChatAgentRuntime` currently normalizes every tool call through `default_paper_id()`. Because `rag_search_context` is included in that default injection set, broad requests like “在 rag 中查询和 agent 相关的内容有哪些，这些内容对应着哪些文章” become scoped to the selected paper. The same run showed a Milvus `Unsupported field type: 0` failure during filtered search, then a later ReAct invalid JSON fallback hid the RAG error from the final response.

## Goals / Non-Goals

**Goals:**

- Make broad RAG chat queries search across the indexed RAG collection.
- Scope RAG queries to the selected paper only when the user explicitly asks about the current/selected paper.
- Preserve RAG tool failures as the primary final response.
- Improve Milvus scalar filter compatibility for `paper_id`.
- Keep warning output concise and actionable.

**Non-Goals:**

- Do not add new CLI commands or change the `rag_search_context` tool schema.
- Do not automatically delete or rebuild existing Milvus collections.
- Do not change PaperStore reading, fulltext reading, debate, or court behavior beyond preserving their current selected-paper injection.

## Decisions

- Add tool-specific selected-paper injection. `rag_search_context` will require explicit current-paper language before injecting `paper_id`; other paper-scoped tools keep current behavior.
- Treat failed tool observations as terminal for the current ReAct loop. This avoids running another LLM step after a concrete tool failure and prevents invalid JSON from replacing the useful error.
- Format failed observations through the existing response path with extra details from `data.rag_log_path` and warnings when present.
- Add or verify a scalar index for `paper_id` when creating or preflighting the Milvus collection. If an existing collection cannot support the required filter, return a clear compatibility error advising manual rebuild/reindex.
- Do not make destructive Milvus repair automatic. Users must explicitly rebuild if an old collection schema/index is incompatible.

## Risks / Trade-offs

- Existing Milvus collections may still fail until rebuilt with compatible schema/indexes. Mitigation: return a clear message that names the collection and recommends reindexing.
- Some user wording may be ambiguous. Mitigation: only inject `paper_id` for explicit current-paper phrases and otherwise prefer broad search.
- Terminal tool failure routing may stop ReAct from trying an alternate tool. Mitigation: apply this to failed observations where surfacing the concrete error is more useful than an additional LLM guess.

## Migration Plan

No data migration is automatic. After deployment, users with incompatible Milvus collections should rebuild the RAG collection and reindex papers manually. Rollback is code-only and does not affect PaperStore or chat logs.

## Open Questions

- None for implementation. Future work can add an explicit RAG collection rebuild command.
