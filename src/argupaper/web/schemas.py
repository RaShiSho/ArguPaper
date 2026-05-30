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
    search_agent_trace_path: str
    web_log_path: str
    analyze_retrieval_loop_enabled: bool


class ApiErrorResponse(BaseModel):
    """Readable error response shape."""

    detail: str
    error_type: str = "Error"
