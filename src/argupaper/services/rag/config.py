"""Configuration models for local RAG services."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MilvusConfig(BaseModel):
    """Milvus connection and collection settings."""

    uri: str = "./data/milvus.db"
    collection: str = "paper_chunks"


class OllamaEmbeddingConfig(BaseModel):
    """Ollama embedding endpoint settings."""

    base_url: str = "http://localhost:11434"
    model: str = "bge-m3"


class RAGConfig(BaseModel):
    """Configuration for local paper RAG.

    This model only carries settings. It must not create network or database
    connections during import or configuration loading.
    """

    enabled: bool = False
    top_k: int = Field(default=6, ge=1)
    chunk_size: int = Field(default=800, ge=1)
    chunk_overlap: int = Field(default=120, ge=0)
    include_references: bool = False
    vector_dim: int = Field(default=1024, ge=1)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    embedding: OllamaEmbeddingConfig = Field(default_factory=OllamaEmbeddingConfig)

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "RAGConfig":
        """Ensure chunk overlap remains smaller than the chunk size."""

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE.")
        return self


__all__ = ["MilvusConfig", "OllamaEmbeddingConfig", "RAGConfig"]
