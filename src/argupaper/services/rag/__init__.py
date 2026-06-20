"""Local RAG service configuration and initialization boundary."""

from argupaper.services.rag.chunker import PaperChunk, PaperChunker
from argupaper.services.rag.config import MilvusConfig, OllamaEmbeddingConfig, RAGConfig
from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.init import (
    RAGServiceSettings,
    build_milvus_vector_store,
    build_ollama_embedding_client,
    build_paper_chunker,
    build_rag_service_settings,
)
from argupaper.services.rag.parser import PaperTextParser, ParsedPaperText, ParsedSection
from argupaper.services.rag.vector_store import MilvusChunk, MilvusSearchResult, MilvusVectorStore

__all__ = [
    "MilvusChunk",
    "MilvusConfig",
    "MilvusSearchResult",
    "MilvusVectorStore",
    "OllamaEmbeddingClient",
    "OllamaEmbeddingConfig",
    "PaperChunk",
    "PaperChunker",
    "PaperTextParser",
    "ParsedPaperText",
    "ParsedSection",
    "RAGConfig",
    "RAGServiceSettings",
    "build_milvus_vector_store",
    "build_ollama_embedding_client",
    "build_paper_chunker",
    "build_rag_service_settings",
]
