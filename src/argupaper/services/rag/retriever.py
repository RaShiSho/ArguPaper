"""RAG retrieval over embedded paper chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.vector_store import MilvusSearchResult, MilvusVectorStore
from argupaper.workflows.errors import ExternalServiceError, InputValidationError


@dataclass(frozen=True)
class RetrievalQuery:
    """Structured query for local RAG retrieval."""

    text: str
    top_k: int = 6
    paper_id: str | None = None
    section_type: str | None = None
    score_threshold: float | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    """One retrieved paper chunk with traceable metadata."""

    chunk_id: str
    paper_id: str
    chunk_index: int
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    section: str | None = None
    section_type: str | None = None
    source: str | None = None
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True)
class RetrievalResult:
    """Result of one RAG retrieval request."""

    query: RetrievalQuery
    chunks: list[RetrievedChunk]
    warnings: list[str] = field(default_factory=list)


class RAGRetriever:
    """Embed a query and search dense paper chunks."""

    def __init__(
        self,
        embedding_client: OllamaEmbeddingClient,
        vector_store: MilvusVectorStore,
        *,
        candidate_multiplier: int = 4,
    ) -> None:
        if candidate_multiplier <= 0:
            raise InputValidationError("candidate_multiplier must be greater than 0.")
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.candidate_multiplier = candidate_multiplier

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Retrieve chunks for one query."""

        normalized_query = self._validate_query(query)
        try:
            query_vector = await self.embedding_client.embed_text(normalized_query.text)
        except ExternalServiceError as exc:
            raise ExternalServiceError(f"RAG query embedding failed: {exc}") from exc

        search_limit = self._search_limit(normalized_query)
        try:
            raw_results = self.vector_store.search(
                query_vector,
                top_k=search_limit,
                paper_id=normalized_query.paper_id,
            )
        except ExternalServiceError as exc:
            raise ExternalServiceError(
                "RAG vector search failed "
                f"(paper_id={normalized_query.paper_id or '*'}; top_k={search_limit}): {exc}"
            ) from exc

        chunks = self._filter_results(raw_results, normalized_query)
        warnings: list[str] = []
        if not chunks:
            warnings.append("No RAG chunks matched the retrieval query.")
        return RetrievalResult(query=normalized_query, chunks=chunks, warnings=warnings)

    def _validate_query(self, query: RetrievalQuery) -> RetrievalQuery:
        text = str(query.text or "").strip()
        if not text:
            raise InputValidationError("RetrievalQuery.text must not be empty.")
        if query.top_k <= 0:
            raise InputValidationError("RetrievalQuery.top_k must be greater than 0.")

        paper_id = str(query.paper_id).strip() if query.paper_id is not None else None
        if paper_id == "":
            paper_id = None

        section_type = str(query.section_type).strip() if query.section_type is not None else None
        if section_type == "":
            section_type = None
        if section_type is not None:
            section_type = self._normalize_section_type(section_type)

        if query.score_threshold is not None and (
            isinstance(query.score_threshold, bool)
            or not isinstance(query.score_threshold, (int, float))
        ):
            raise InputValidationError("RetrievalQuery.score_threshold must be numeric.")

        return RetrievalQuery(
            text=text,
            top_k=int(query.top_k),
            paper_id=paper_id,
            section_type=section_type,
            score_threshold=(
                float(query.score_threshold) if query.score_threshold is not None else None
            ),
        )

    def _search_limit(self, query: RetrievalQuery) -> int:
        if query.section_type is None and query.score_threshold is None:
            return query.top_k
        return max(query.top_k, query.top_k * self.candidate_multiplier)

    def _filter_results(
        self,
        results: list[MilvusSearchResult],
        query: RetrievalQuery,
    ) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        for result in results:
            chunk = self._to_retrieved_chunk(result)
            if query.paper_id is not None and chunk.paper_id != query.paper_id:
                continue
            if query.section_type is not None and chunk.section_type != query.section_type:
                continue
            if query.score_threshold is not None and chunk.score < query.score_threshold:
                continue
            chunks.append(chunk)
            if len(chunks) >= query.top_k:
                break
        return chunks

    def _to_retrieved_chunk(self, result: MilvusSearchResult) -> RetrievedChunk:
        metadata = dict(result.metadata)
        section_type = metadata.get("section_type")
        return RetrievedChunk(
            chunk_id=result.chunk_id,
            paper_id=result.paper_id,
            chunk_index=result.chunk_index,
            text=result.text,
            score=float(result.score),
            metadata=metadata,
            section=result.section or self._none_if_empty(metadata.get("section_title")),
            section_type=self._normalize_section_type(str(section_type)) if section_type else None,
            source=result.source,
            page_start=self._optional_int(metadata.get("page_start")),
            page_end=self._optional_int(metadata.get("page_end")),
        )

    def _normalize_section_type(self, value: str) -> str:
        return "_".join(str(value or "").strip().casefold().replace("-", "_").split())

    def _optional_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _none_if_empty(self, value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None


__all__ = ["RAGRetriever", "RetrievalQuery", "RetrievalResult", "RetrievedChunk"]
