"""Workflow wrapper for local RAG operations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

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

ProgressCallback = Callable[[str], None] | None


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

    def status(self, progress_callback: ProgressCallback = None) -> RAGStatusResult:
        """Return resolved RAG configuration without connecting to services."""

        run_id, log_path = self._new_run_log_path("status")
        self._emit(log_path, run_id, "run_start", "running", progress_callback, "Reading RAG configuration.")
        rag = self.config.rag
        result = RAGStatusResult(
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
            run_log_path=str(log_path),
        )
        self._emit(
            log_path,
            run_id,
            "status_ready",
            "success",
            progress_callback,
            "RAG configuration loaded.",
            rag_enabled=rag.enabled,
            ollama_base_url=rag.embedding.base_url,
            embedding_model=rag.embedding.model,
            milvus_uri=rag.milvus.uri,
            milvus_collection=rag.milvus.collection,
        )
        self._emit(log_path, run_id, "run_summary", "completed", progress_callback, "RAG status complete.")
        return result

    async def index_paper(
        self,
        options: RAGIndexOptions,
        progress_callback: ProgressCallback = None,
    ) -> RAGIndexResult:
        """Index one PaperStore paper."""

        run_id, log_path = self._new_run_log_path("index")
        try:
            paper_id = self._validate_paper_id(options.paper_id)
            self._emit(
                log_path,
                run_id,
                "run_start",
                "running",
                progress_callback,
                f"Starting RAG index for paper_id={paper_id}.",
                paper_id=paper_id,
                dry_run=options.dry_run,
            )
            self._emit(
                log_path,
                run_id,
                "index_prepare",
                "running",
                progress_callback,
                "Resolving paper, parsing full text, and building chunks.",
                paper_id=paper_id,
            )
            stats = await self.indexer.index_paper(paper_id, dry_run=options.dry_run)
        except Exception as exc:
            self._emit_error(
                log_path,
                run_id,
                "index_failed",
                exc,
                progress_callback,
                paper_id=str(options.paper_id or "").strip(),
            )
            raise
        self._emit(
            log_path,
            run_id,
            "index_complete",
            "success",
            progress_callback,
            f"RAG index complete for paper_id={stats.paper_id}: {stats.chunk_count} chunk(s).",
            paper_id=stats.paper_id,
            chunk_count=stats.chunk_count,
            embedding_dim=stats.embedding_dim,
            skipped_sections=stats.skipped_sections,
            warnings=stats.warnings,
            dry_run=options.dry_run,
        )
        self._emit(log_path, run_id, "run_summary", "completed", progress_callback, "RAG index run complete.")
        return RAGIndexResult(
            paper_id=stats.paper_id,
            chunk_count=stats.chunk_count,
            embedding_dim=stats.embedding_dim,
            skipped_sections=stats.skipped_sections,
            warnings=stats.warnings,
            dry_run=options.dry_run,
            run_log_path=str(log_path),
        )

    async def delete_paper(
        self,
        options: RAGDeleteOptions,
        progress_callback: ProgressCallback = None,
    ) -> RAGDeleteResult:
        """Delete one paper's chunks from vector storage."""

        run_id, log_path = self._new_run_log_path("delete")
        try:
            paper_id = self._validate_paper_id(options.paper_id)
            self._emit(
                log_path,
                run_id,
                "run_start",
                "running",
                progress_callback,
                f"Deleting RAG chunks for paper_id={paper_id}.",
                paper_id=paper_id,
            )
            deleted_count = self.vector_store.delete_by_paper(paper_id)
        except Exception as exc:
            self._emit_error(
                log_path,
                run_id,
                "delete_failed",
                exc,
                progress_callback,
                paper_id=str(options.paper_id or "").strip(),
            )
            raise
        self._emit(
            log_path,
            run_id,
            "delete_complete",
            "success",
            progress_callback,
            f"RAG delete complete for paper_id={paper_id}.",
            paper_id=paper_id,
            deleted_count=deleted_count,
        )
        self._emit(log_path, run_id, "run_summary", "completed", progress_callback, "RAG delete run complete.")
        return RAGDeleteResult(paper_id=paper_id, deleted_count=deleted_count, run_log_path=str(log_path))

    async def search(
        self,
        options: RAGSearchOptions,
        progress_callback: ProgressCallback = None,
    ) -> RAGSearchResult:
        """Search indexed paper chunks."""

        run_id, log_path = self._new_run_log_path("search")
        try:
            content = str(options.content or "").strip()
            if not content:
                raise InputValidationError("RAG search content must not be empty.")

            top_k = options.top_k if options.top_k is not None else self.config.rag.top_k
            if top_k <= 0:
                raise InputValidationError("--top-k must be greater than 0.")

            paper_id = self._validate_optional_paper_id(options.paper_id)
            self._emit(
                log_path,
                run_id,
                "run_start",
                "running",
                progress_callback,
                "Starting RAG search.",
                paper_id=paper_id,
                top_k=top_k,
                section_type=options.section_type,
                score_threshold=options.score_threshold,
            )
            self._emit(
                log_path,
                run_id,
                "embedding_query",
                "running",
                progress_callback,
                "Embedding query and searching vector store.",
                paper_id=paper_id,
            )
            retrieval = await self.retriever.retrieve(
                RetrievalQuery(
                    text=content,
                    top_k=top_k,
                    paper_id=paper_id,
                    section_type=options.section_type,
                    score_threshold=options.score_threshold,
                )
            )
        except Exception as exc:
            self._emit_error(
                log_path,
                run_id,
                "search_failed",
                exc,
                progress_callback,
                paper_id=str(options.paper_id or "").strip() or None,
            )
            raise
        self._emit(
            log_path,
            run_id,
            "search_results",
            "success",
            progress_callback,
            f"RAG search returned {len(retrieval.chunks)} chunk(s).",
            paper_id=paper_id,
            chunk_count=len(retrieval.chunks),
            warnings=retrieval.warnings,
        )
        context = ContextBuilder(max_chars=options.context_max_chars).build_context(retrieval.chunks)
        self._emit(
            log_path,
            run_id,
            "context_built",
            "success",
            progress_callback,
            f"Built RAG context with {len(context)} character(s).",
            context_chars=len(context),
        )
        self._emit(log_path, run_id, "run_summary", "completed", progress_callback, "RAG search run complete.")
        return RAGSearchResult(
            content=content,
            paper_id=paper_id,
            top_k=top_k,
            chunks=retrieval.chunks,
            context=context,
            warnings=retrieval.warnings,
            run_log_path=str(log_path),
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

    def _new_run_log_path(self, operation: str) -> tuple[str, Path]:
        run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{operation}-{uuid4().hex[:8]}"
        log_path = Path(self.config.log.rag_path) / f"{run_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return run_id, log_path

    def _emit(
        self,
        log_path: Path,
        run_id: str,
        event: str,
        status: str,
        progress_callback: ProgressCallback,
        message: str,
        **details: object,
    ) -> None:
        if progress_callback is not None:
            progress_callback(message)
        payload: dict[str, object] = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "status": status,
            "message": message,
        }
        payload.update(details)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _emit_error(
        self,
        log_path: Path,
        run_id: str,
        event: str,
        exc: Exception,
        progress_callback: ProgressCallback,
        **details: object,
    ) -> None:
        self._emit(
            log_path,
            run_id,
            event,
            "failed",
            progress_callback,
            f"RAG operation failed: {type(exc).__name__}: {exc}",
            error_type=type(exc).__name__,
            error=str(exc),
            **details,
        )


__all__ = ["RAGWorkflow"]
