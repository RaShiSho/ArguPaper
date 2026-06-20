"""Lazy initialization boundary for RAG services."""

from __future__ import annotations

from dataclasses import dataclass

from argupaper.services.rag.config import RAGConfig
from argupaper.services.rag.embedding import OllamaEmbeddingClient


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


__all__ = [
    "RAGServiceSettings",
    "build_ollama_embedding_client",
    "build_rag_service_settings",
]
