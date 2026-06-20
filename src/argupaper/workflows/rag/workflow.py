"""Workflow wrapper for local RAG operations."""

from __future__ import annotations

from argupaper.config import Config
from argupaper.memory.paper_store import PaperStore
from argupaper.services.rag import (
    ContextBuilder,
    RAGIndexer,
    RAGRetriever,
    RetrievalQuery,
    build_milvus_vector_store,
    build_ollama_embedding_client,
    build_paper_chunker,
)
from argupaper.workflows.errors import InputValidationError
from argupaper.workflows.rag.options import RAGDeleteOptions, RAGIndexOptions, RAGSearchOptions
from argupaper.workflows.rag.result import (
    RAGDeleteResult,
    RAGIndexResult,
    RAGSearchResult,
    RAGStatusResult,
)


class RAGWorkflow:
    """Workflow boundary for local RAG status, indexing, deletion, and search."""

    def __init__(self, config: Config, paper_store: PaperStore | None = None) -> None:
        self.config = config
        self.paper_store = paper_store or PaperStore(storage_path=config.paper_storage_path)
        self.embedding_client = build_ollama_embedding_client(config.rag)
        self.vector_store = build_milvus_vector_store(config.rag)
        self.chunker = build_paper_chunker(config.rag, pdf_cache_dir=config.pdf.cache_dir)
        self.indexer = RAGIndexer(
            paper_store=self.paper_store,
            chunker=self.chunker,
            embedding_client=self.embedding_client,
            vector_store=self.vector_store,
        )
        self.retriever = RAGRetriever(
            embedding_client=self.embedding_client,
            vector_store=self.vector_store,
        )

    def status(self) -> RAGStatusResult:
        """Return resolved RAG configuration without connecting to services."""

        rag = self.config.rag
        return RAGStatusResult(
            rag_enabled=rag.enabled,
            ollama_base_url=rag.embedding.base_url,
            ollama_embed_model=rag.embedding.model,
            milvus_uri=rag.milvus.uri,
            milvus_collection=rag.milvus.collection,
            top_k=rag.top_k,
            chunk_size=rag.chunk_size,
            chunk_overlap=rag.chunk_overlap,
            include_references=rag.include_references,
            vector_dim=rag.vector_dim,
        )

    async def index_paper(self, options: RAGIndexOptions) -> RAGIndexResult:
        """Index one PaperStore paper."""

        paper_id = self._validate_paper_id(options.paper_id)
        stats = await self.indexer.index_paper(paper_id, dry_run=options.dry_run)
        return RAGIndexResult(
            paper_id=stats.paper_id,
            chunk_count=stats.chunk_count,
            embedding_dim=stats.embedding_dim,
            skipped_sections=stats.skipped_sections,
            warnings=stats.warnings,
            dry_run=options.dry_run,
        )

    async def delete_paper(self, options: RAGDeleteOptions) -> RAGDeleteResult:
        """Delete one paper's chunks from vector storage."""

        paper_id = self._validate_paper_id(options.paper_id)
        deleted_count = self.vector_store.delete_by_paper(paper_id)
        return RAGDeleteResult(paper_id=paper_id, deleted_count=deleted_count)

    async def search(self, options: RAGSearchOptions) -> RAGSearchResult:
        """Search indexed paper chunks."""

        content = str(options.content or "").strip()
        if not content:
            raise InputValidationError("RAG search content must not be empty.")

        top_k = options.top_k if options.top_k is not None else self.config.rag.top_k
        if top_k <= 0:
            raise InputValidationError("--top-k must be greater than 0.")

        paper_id = self._validate_optional_paper_id(options.paper_id)
        retrieval = await self.retriever.retrieve(
            RetrievalQuery(
                text=content,
                top_k=top_k,
                paper_id=paper_id,
                section_type=options.section_type,
                score_threshold=options.score_threshold,
            )
        )
        context = ContextBuilder(max_chars=options.context_max_chars).build_context(retrieval.chunks)
        return RAGSearchResult(
            content=content,
            paper_id=paper_id,
            top_k=top_k,
            chunks=retrieval.chunks,
            context=context,
            warnings=retrieval.warnings,
        )

    async def close(self) -> None:
        """Close lazy external service clients if they were opened."""

        await self.embedding_client.close()
        self.vector_store.close()

    def _validate_paper_id(self, paper_id: str) -> str:
        normalized = str(paper_id or "").strip()
        if not normalized:
            raise InputValidationError("paper_id must not be empty.")
        return normalized

    def _validate_optional_paper_id(self, paper_id: str | None) -> str | None:
        if paper_id is None:
            return None
        normalized = str(paper_id).strip()
        return normalized or None


__all__ = ["RAGWorkflow"]
