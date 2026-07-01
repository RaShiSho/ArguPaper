## ADDED Requirements

### Requirement: Broad chat RAG searches are not scoped to selected paper

The chat runtime SHALL call `rag_search_context` without `paper_id` when the user asks for a broad RAG search across indexed papers.

#### Scenario: Broad RAG query with selected paper

- **WHEN** a paper is selected and the user asks “在 rag 中查询和 agent 相关的内容有哪些，这些内容对应着哪些文章”
- **THEN** the `rag_search_context` tool call MUST include a query and MUST NOT include `paper_id`

### Requirement: Explicit current-paper RAG searches are scoped

The chat runtime SHALL inject the selected `paper_id` into `rag_search_context` only when the user explicitly scopes the RAG query to the current or selected paper.

#### Scenario: Current paper RAG query

- **WHEN** a paper is selected and the user asks “在这篇论文的 rag 中查询 agent 后门相关内容”
- **THEN** the `rag_search_context` tool call MUST include the selected paper id

### Requirement: RAG tool failures are user-visible

The chat runtime SHALL preserve a failed RAG tool observation as the primary final response instead of replacing it with a later ReAct JSON parsing failure.

#### Scenario: RAG tool returns failure

- **WHEN** `rag_search_context` returns `ok=false`
- **THEN** the final chat response MUST include the RAG failure summary and MUST NOT claim only that the natural-language Agent is unavailable

### Requirement: Milvus paper filters are compatibility checked

The RAG vector store SHALL support `paper_id` scalar filtering for scoped search or return a clear compatibility error that names the collection and recommends manual rebuild/reindex.

#### Scenario: Incompatible collection filter

- **WHEN** Milvus rejects a scoped search because the collection cannot support the `paper_id` filter
- **THEN** the error summary MUST explain that the RAG collection is incompatible and requires manual rebuild/reindex

## MODIFIED Requirements

### Requirement: Chat tool execution preserves RAG tool errors

The LangGraph chat agent runtime SHALL execute registered tools through the tool layer and SHALL route concrete failed observations to a user-facing terminal response when another ReAct step would obscure the failure.

#### Scenario: Failed observation before invalid ReAct response

- **WHEN** a tool returns `ok=false` and a subsequent ReAct response is invalid JSON
- **THEN** the final response MUST prioritize the tool failure over the invalid JSON reason
