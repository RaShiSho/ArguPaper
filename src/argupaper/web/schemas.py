"""Typed schemas for the local web workbench API."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from argupaper.workflows.models import AnalyzeWorkflowResult, SearchAgentResult, SearchSource


JobStatus = Literal["queued", "running", "succeeded", "failed"]


class SearchRequest(BaseModel):
    """Request body for web paper search."""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    source: SearchSource = "both"
    verbose: bool = False


class SearchResponse(BaseModel):
    """Search response returned to the React workbench."""

    result: SearchAgentResult


class AnalyzeSubmitResponse(BaseModel):
    """Response returned after creating an analyze job."""

    job_id: str
    status: JobStatus


class WorkflowSubmitResponse(BaseModel):
    """Response returned after creating a generic workflow job."""

    job_id: str
    status: JobStatus


class JobProgressMessage(BaseModel):
    """One observable progress message from a background job."""

    message: str
    timestamp: datetime


class AnalyzeJobStatusResponse(BaseModel):
    """Snapshot of one background analyze job."""

    job_id: str
    status: JobStatus
    upload_filename: str
    created_at: datetime
    updated_at: datetime
    progress: list[JobProgressMessage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    result: Optional[AnalyzeWorkflowResult] = None
    error: Optional[str] = None


class WorkflowJobStatusResponse(BaseModel):
    """Snapshot of one generic workflow job."""

    job_id: str
    kind: str
    label: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    progress: list[JobProgressMessage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    result: Any = None
    error: Optional[str] = None


class ConvertPathRequest(BaseModel):
    """Request body for converting a local PDF path or folder path."""

    pdf_path: Optional[str] = None
    folder_path: Optional[str] = None
    output_path: Optional[str] = None
    force: bool = False


class DebateRequest(BaseModel):
    """Request body for running debate on a saved paper or local PDF path."""

    paper: str = Field(..., min_length=1)
    output_path: Optional[str] = None
    save_report: bool = False
    rounds: int = Field(default=3, ge=1, le=20)
    force: bool = False
    verbose: bool = False


class CourtRequest(BaseModel):
    """Request body for running paper court on a saved paper."""

    paper_id: str = Field(..., min_length=1)
    output_path: Optional[str] = None
    rounds: int = Field(default=2, ge=1, le=20)
    verbose: bool = False


class RAGIndexRequest(BaseModel):
    """Request body for indexing one saved paper into RAG."""

    paper_id: str = Field(..., min_length=1)
    dry_run: bool = False


class RAGDeleteRequest(BaseModel):
    """Request body for deleting one saved paper from RAG."""

    paper_id: str = Field(..., min_length=1)


class RAGSearchRequest(BaseModel):
    """Request body for local RAG search."""

    content: str = Field(..., min_length=1)
    paper_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=100)
    section_type: Optional[str] = None
    score_threshold: Optional[float] = None
    context_max_chars: int = Field(default=12000, ge=1000, le=100000)


class ChatSessionResponse(BaseModel):
    """Response returned after creating a chat session."""

    session_id: str


class ChatTurnRequest(BaseModel):
    """Request body for one chat agent turn."""

    message: str = Field(..., min_length=1)


class ChatTurnResponse(BaseModel):
    """Response returned by one chat agent turn."""

    response: str
    interrupted: bool = False
    warnings: list[str] = Field(default_factory=list)
    selected_paper: Any = None
    log_path: Optional[str] = None


class PaperListResponse(BaseModel):
    """Saved paper records response."""

    records: list[dict[str, Any]] = Field(default_factory=list)


class PaperDetailResponse(BaseModel):
    """One saved paper record response."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    abstract: dict[str, Any] = Field(default_factory=dict)
    report: str = ""
    markdown: str = ""


class ConfigStatusResponse(BaseModel):
    """Non-secret configuration status for the local workbench."""

    mineru_api_configured: bool
    semantic_scholar_configured: bool
    serpapi_configured: bool
    paper_storage_path: str
    cache_path: str
    log_path: str
    search_log_path: str
    convert_log_path: str
    web_log_path: str
    rag_log_path: str
    analyze_retrieval_loop_enabled: bool


class ApiErrorResponse(BaseModel):
    """Readable error response shape."""

    detail: str
    error_type: str = "Error"
