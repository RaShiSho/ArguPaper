"""Local RAG service configuration and initialization boundary."""

from argupaper.services.rag.config import MilvusConfig, OllamaEmbeddingConfig, RAGConfig
from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.init import (
    RAGServiceSettings,
    build_ollama_embedding_client,
    build_rag_service_settings,
)

__all__ = [
    "MilvusConfig",
    "OllamaEmbeddingClient",
    "OllamaEmbeddingConfig",
    "RAGConfig",
    "RAGServiceSettings",
    "build_ollama_embedding_client",
    "build_rag_service_settings",
]
