"""Single-paper RAG indexing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from argupaper.memory.paper_store import PaperStore
from argupaper.services.rag.chunker import PaperChunk, PaperChunker
from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.vector_store import MilvusChunk, MilvusVectorStore
from argupaper.workflows.errors import ExternalServiceError, InputValidationError


@dataclass(frozen=True)
class RAGIndexStats:
    """Statistics returned after indexing one paper."""

    paper_id: str
    chunk_count: int
    embedding_dim: int | None
    skipped_sections: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RAGIndexer:
    """Index one PaperStore paper into the configured vector store."""

    def __init__(
        self,
        paper_store: PaperStore,
        chunker: PaperChunker,
        embedding_client: OllamaEmbeddingClient,
        vector_store: MilvusVectorStore,
        *,
        embedding_batch_size: int = 16,
    ) -> None:
        if embedding_batch_size <= 0:
            raise InputValidationError("embedding_batch_size must be greater than 0.")

        self.paper_store = paper_store
        self.chunker = chunker
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.embedding_batch_size = embedding_batch_size

    async def index_paper(self, paper_id: str, *, dry_run: bool = False) -> RAGIndexStats:
        """Index one paper from PaperStore into Milvus."""

        normalized_paper_id = self._validate_requested_paper_id(paper_id)
        paper = await self.paper_store.get_paper(normalized_paper_id)
        if paper is None:
            raise InputValidationError(f"Paper not found for RAG indexing: {normalized_paper_id}")

        metadata = self._paper_metadata(paper)
        resolved_paper_id = self._resolve_paper_id(normalized_paper_id, metadata)
        source_path = self._source_path(resolved_paper_id)

        parsed = self.chunker.parser.parse_path(source_path)
        parsed = replace(parsed, metadata={**parsed.metadata, **metadata})
        chunks = self.chunker.chunk_parsed(parsed, paper_id=resolved_paper_id)
        skipped_sections = self._skipped_sections(parsed.sections)
        if not chunks:
            raise InputValidationError(
                "RAG indexing produced no chunks "
                f"(paper_id={resolved_paper_id}; source_path={source_path})."
            )

        warnings: list[str] = []
        if dry_run:
            warnings.append("dry_run enabled; skipped embedding, Milvus delete, and Milvus upsert.")
            return RAGIndexStats(
                paper_id=resolved_paper_id,
                chunk_count=len(chunks),
                embedding_dim=None,
                skipped_sections=skipped_sections,
                warnings=warnings,
            )

        embeddings, embedding_dim = await self._embed_chunks(resolved_paper_id, chunks)
        milvus_chunks = self._to_milvus_chunks(chunks, embeddings)
        self._ensure_vector_store_ready(resolved_paper_id, embedding_dim)
        self._delete_existing_chunks(resolved_paper_id)
        self._upsert_chunks(resolved_paper_id, milvus_chunks)

        return RAGIndexStats(
            paper_id=resolved_paper_id,
            chunk_count=len(chunks),
            embedding_dim=embedding_dim,
            skipped_sections=skipped_sections,
            warnings=warnings,
        )

    async def reindex_paper(self, paper_id: str, *, dry_run: bool = False) -> RAGIndexStats:
        """Rebuild one paper index. First version is equivalent to index_paper."""

        return await self.index_paper(paper_id, dry_run=dry_run)

    async def _embed_chunks(
        self,
        paper_id: str,
        chunks: list[PaperChunk],
    ) -> tuple[list[list[float]], int]:
        embeddings: list[list[float]] = []
        expected_dim: int | None = None

        for batch_number, start in enumerate(range(0, len(chunks), self.embedding_batch_size), start=1):
            batch = chunks[start : start + self.embedding_batch_size]
            texts = [chunk.text for chunk in batch]
            try:
                batch_embeddings = await self.embedding_client.embed_texts(texts)
            except ExternalServiceError as exc:
                raise ExternalServiceError(
                    "RAG embedding failed "
                    f"(paper_id={paper_id}; batch={batch_number}; batch_size={len(batch)}): {exc}"
                ) from exc

            if len(batch_embeddings) != len(batch):
                raise ExternalServiceError(
                    "RAG embedding response count mismatch "
                    f"(paper_id={paper_id}; batch={batch_number}; "
                    f"expected={len(batch)}; actual={len(batch_embeddings)})."
                )

            for embedding_index, embedding in enumerate(batch_embeddings):
                dimension = self._embedding_dimension(
                    embedding,
                    paper_id=paper_id,
                    batch_number=batch_number,
                    embedding_index=embedding_index,
                )
                if expected_dim is None:
                    expected_dim = dimension
                elif dimension != expected_dim:
                    raise ExternalServiceError(
                        "RAG embedding dimension mismatch "
                        f"(paper_id={paper_id}; expected={expected_dim}; actual={dimension}; "
                        f"batch={batch_number}; index={embedding_index})."
                    )
                embeddings.append(embedding)

        if expected_dim is None:
            raise ExternalServiceError(f"RAG embedding produced no vectors (paper_id={paper_id}).")
        return embeddings, expected_dim

    def _ensure_vector_store_ready(self, paper_id: str, embedding_dim: int) -> None:
        try:
            self.vector_store.ensure_collection(embedding_dim)
        except ExternalServiceError as exc:
            raise ExternalServiceError(
                "RAG Milvus collection preflight failed before deleting old chunks "
                f"(paper_id={paper_id}; stage=ensure_collection): {exc}"
            ) from exc

    def _delete_existing_chunks(self, paper_id: str) -> None:
        try:
            self.vector_store.delete_by_paper(paper_id)
        except ExternalServiceError as exc:
            raise ExternalServiceError(
                f"RAG Milvus delete failed (paper_id={paper_id}; stage=delete_old_chunks): {exc}"
            ) from exc

    def _upsert_chunks(self, paper_id: str, chunks: list[MilvusChunk]) -> None:
        try:
            self.vector_store.upsert(chunks)
        except ExternalServiceError as exc:
            raise ExternalServiceError(
                "RAG Milvus upsert failed after old chunks were deleted "
                f"(paper_id={paper_id}; stage=upsert_new_chunks): {exc}"
            ) from exc

    def _to_milvus_chunks(
        self,
        chunks: list[PaperChunk],
        embeddings: list[list[float]],
    ) -> list[MilvusChunk]:
        if len(chunks) != len(embeddings):
            raise ExternalServiceError(
                "RAG internal chunk/vector count mismatch "
                f"(chunks={len(chunks)}; embeddings={len(embeddings)})."
            )

        milvus_chunks: list[MilvusChunk] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if not chunk.paper_id:
                raise InputValidationError(f"RAG chunk is missing paper_id: {chunk.chunk_id}")
            metadata = dict(chunk.metadata)
            metadata["page_start"] = chunk.page_start
            metadata["page_end"] = chunk.page_end
            metadata["section_title"] = chunk.section_title
            metadata["section_type"] = chunk.section_type
            milvus_chunks.append(
                MilvusChunk(
                    chunk_id=chunk.chunk_id,
                    paper_id=chunk.paper_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    vector=embedding,
                    metadata=metadata,
                    section=chunk.section_title,
                    source=chunk.source_path,
                )
            )
        return milvus_chunks

    def _embedding_dimension(
        self,
        embedding: list[float],
        *,
        paper_id: str,
        batch_number: int,
        embedding_index: int,
    ) -> int:
        if not embedding:
            raise ExternalServiceError(
                "RAG embedding response contains an empty vector "
                f"(paper_id={paper_id}; batch={batch_number}; index={embedding_index})."
            )
        return len(embedding)

    def _paper_metadata(self, paper: dict[str, Any]) -> dict[str, Any]:
        metadata = paper.get("metadata", {})
        return dict(metadata) if isinstance(metadata, dict) else {}

    def _resolve_paper_id(self, requested_paper_id: str, metadata: dict[str, Any]) -> str:
        metadata_paper_id = metadata.get("paper_id")
        resolved = str(metadata_paper_id or requested_paper_id).strip()
        if not resolved:
            raise InputValidationError(f"Paper metadata does not contain a valid paper_id: {requested_paper_id}")
        return self._validate_paper_id_path_segment(resolved)

    def _source_path(self, paper_id: str) -> Path:
        source_path = self.paper_store.storage_path / paper_id / "paper.md"
        if not source_path.exists():
            raise InputValidationError(
                "Paper Markdown source is missing for RAG indexing "
                f"(paper_id={paper_id}; source_path={source_path})."
            )
        return source_path

    def _validate_requested_paper_id(self, paper_id: str) -> str:
        normalized = str(paper_id or "").strip()
        if not normalized:
            raise InputValidationError("paper_id is required for RAG indexing.")
        return self._validate_paper_id_path_segment(normalized)

    def _validate_paper_id_path_segment(self, paper_id: str) -> str:
        if paper_id in {".", ".."} or any(separator in paper_id for separator in ("/", "\\")):
            raise InputValidationError(f"Invalid paper_id for RAG indexing: {paper_id}")
        return paper_id

    def _skipped_sections(self, sections: list[Any]) -> list[str]:
        if self.chunker.include_references:
            return []
        skipped = {
            str(section.section_type)
            for section in sections
            if getattr(section, "section_type", None) == "references" and str(section.text or "").strip()
        }
        return sorted(skipped)


__all__ = ["RAGIndexer", "RAGIndexStats"]
