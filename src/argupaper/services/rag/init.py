"""Lazy initialization boundary for RAG services."""

from __future__ import annotations

from dataclasses import dataclass

from argupaper.memory.paper_store import PaperStore
from argupaper.services.rag.config import RAGConfig
from argupaper.services.rag.chunker import PaperChunker
from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.indexer import RAGIndexer
from argupaper.services.rag.parser import PaperTextParser
from argupaper.services.rag.vector_store import MilvusVectorStore


@dataclass(frozen=True)
class RAGServiceSettings:
    """Resolved RAG settings for future service initialization.

    This is intentionally a settings-only object for now. Future Milvus and
    Ollama clients should be constructed behind this boundary, not at import
    time or during general config loading.
    """

    config: RAGConfig


def build_rag_service_settings(config: RAGConfig) -> RAGServiceSettings:
    """Return resolved RAG service settings without opening external connections."""

    return RAGServiceSettings(config=config)


def build_ollama_embedding_client(config: RAGConfig) -> OllamaEmbeddingClient:
    """Build an Ollama embedding client without opening external connections."""

    return OllamaEmbeddingClient(config.embedding)


def build_paper_chunker(
    config: RAGConfig,
    *,
    pdf_cache_dir: str = "./data/cache",
) -> PaperChunker:
    """Build a paper chunker without reading files or opening external connections."""

    return PaperChunker(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        include_references=config.include_references,
        parser=PaperTextParser(pdf_cache_dir=pdf_cache_dir),
    )


def build_milvus_vector_store(config: RAGConfig) -> MilvusVectorStore:
    """Build a Milvus vector store without opening external connections."""

    return MilvusVectorStore(config.milvus, default_dimension=config.vector_dim)


def build_rag_indexer(
    config: RAGConfig,
    *,
    paper_store: PaperStore,
    pdf_cache_dir: str = "./data/cache",
) -> RAGIndexer:
    """Build a single-paper RAG indexer without opening external connections."""

    return RAGIndexer(
        paper_store=paper_store,
        chunker=build_paper_chunker(config, pdf_cache_dir=pdf_cache_dir),
        embedding_client=build_ollama_embedding_client(config),
        vector_store=build_milvus_vector_store(config),
    )


__all__ = [
    "RAGServiceSettings",
    "build_milvus_vector_store",
    "build_ollama_embedding_client",
    "build_paper_chunker",
    "build_rag_indexer",
    "build_rag_service_settings",
]
