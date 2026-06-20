"""RAG workflow options."""

from pydantic import BaseModel, Field


class RAGIndexOptions(BaseModel):
    """Options for indexing one paper into RAG storage."""

    paper_id: str
    dry_run: bool = False


class RAGDeleteOptions(BaseModel):
    """Options for deleting one paper from RAG storage."""

    paper_id: str


class RAGSearchOptions(BaseModel):
    """Options for searching local RAG storage."""

    content: str
    paper_id: str | None = None
    top_k: int | None = None
    section_type: str | None = None
    score_threshold: float | None = None
    context_max_chars: int = Field(default=12000, ge=1)


__all__ = ["RAGDeleteOptions", "RAGIndexOptions", "RAGSearchOptions"]
