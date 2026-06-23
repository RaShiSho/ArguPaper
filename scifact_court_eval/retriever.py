"""SciFact-specific retriever adapter for PaperCourtGraph."""

from __future__ import annotations

from argupaper.config import Config
from argupaper.services.rag import (
    MilvusConfig,
    MilvusSearchResult,
    MilvusVectorStore,
    OllamaEmbeddingClient,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)
from argupaper.workflows.errors import InputValidationError

from scifact_court_eval.indexer import SCIFACT_COLLECTION, SCIFACT_PAPER_ID


class ScifactRAGRetriever:
    """Retrieve SciFact sentence chunks from the isolated eval collection."""

    def __init__(
        self,
        config: Config,
        *,
        top_k: int,
        collection: str = SCIFACT_COLLECTION,
    ) -> None:
        self.top_k = top_k
        self.embedding_client = OllamaEmbeddingClient(config.rag.embedding)
        self.vector_store = MilvusVectorStore(
            MilvusConfig(uri=config.rag.milvus.uri, collection=collection),
            default_dimension=config.rag.vector_dim,
        )

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Search the SciFact collection, ignoring court's synthetic paper_id."""

        text = str(query.text or "").strip()
        if not text:
            raise InputValidationError("SciFact retrieval query must not be empty.")
        top_k = query.top_k if query.top_k > 0 else self.top_k
        top_k = max(top_k, self.top_k)
        query_vector = await self.embedding_client.embed_text(text)
        raw_results = self.vector_store.search(
            query_vector,
            top_k=top_k,
            paper_id=SCIFACT_PAPER_ID,
        )
        chunks = [self._to_retrieved_chunk(item) for item in raw_results[:top_k]]
        warnings = [] if chunks else ["No SciFact chunks matched the retrieval query."]
        return RetrievalResult(
            query=RetrievalQuery(text=text, top_k=top_k, paper_id=None),
            chunks=chunks,
            warnings=warnings,
        )

    async def close(self) -> None:
        """Close network and Milvus clients."""

        await self.embedding_client.close()
        self.vector_store.close()

    def _to_retrieved_chunk(self, result: MilvusSearchResult) -> RetrievedChunk:
        metadata = dict(result.metadata)
        doc_id = str(metadata.get("doc_id", "unknown"))
        sentence_idx = str(metadata.get("sentence_idx", "unknown"))
        return RetrievedChunk(
            chunk_id=result.chunk_id,
            paper_id=f"scifact:{doc_id}",
            chunk_index=int(result.chunk_index),
            text=result.text,
            score=float(result.score),
            metadata=metadata,
            section="abstract",
            section_type="abstract",
            source=str(metadata.get("source") or result.source or "scifact/corpus.jsonl"),
            page_start=None,
            page_end=None,
        )

