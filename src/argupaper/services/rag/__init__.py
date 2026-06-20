"""Local RAG service configuration and initialization boundary."""

from argupaper.services.rag.config import MilvusConfig, OllamaEmbeddingConfig, RAGConfig
from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.init import (
    RAGServiceSettings,
    build_milvus_vector_store,
    build_ollama_embedding_client,
    build_rag_service_settings,
)
from argupaper.services.rag.vector_store import MilvusChunk, MilvusSearchResult, MilvusVectorStore

__all__ = [
    "MilvusChunk",
    "MilvusConfig",
    "MilvusSearchResult",
    "MilvusVectorStore",
    "OllamaEmbeddingClient",
    "OllamaEmbeddingConfig",
    "RAGConfig",
    "RAGServiceSettings",
    "build_milvus_vector_store",
    "build_ollama_embedding_client",
    "build_rag_service_settings",
]
