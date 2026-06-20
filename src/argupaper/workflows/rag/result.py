"""RAG workflow result models."""

from pydantic import BaseModel, Field

from argupaper.services.rag import RetrievedChunk


class RAGStatusResult(BaseModel):
    """Resolved local RAG configuration summary."""

    rag_enabled: bool
    ollama_base_url: str
    ollama_embed_model: str
    milvus_uri: str
    milvus_collection: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    include_references: bool
    vector_dim: int
    run_log_path: str | None = None


class RAGIndexResult(BaseModel):
    """Result for single-paper indexing."""

    paper_id: str
    chunk_count: int
    embedding_dim: int | None = None
    skipped_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dry_run: bool = False
    run_log_path: str | None = None


class RAGDeleteResult(BaseModel):
    """Result for deleting one paper from vector storage."""

    paper_id: str
    deleted_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    run_log_path: str | None = None


class RAGSearchResult(BaseModel):
    """Result for local RAG search."""

    content: str
    paper_id: str | None = None
    top_k: int
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    context: str = ""
    warnings: list[str] = Field(default_factory=list)
    run_log_path: str | None = None


__all__ = ["RAGDeleteResult", "RAGIndexResult", "RAGSearchResult", "RAGStatusResult"]
