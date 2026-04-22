"""Shared models used between CLI commands and workflows."""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


SearchSource = Literal["semantic_scholar", "arxiv", "both"]


class SearchResult(BaseModel):
    """Normalized paper search result."""

    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: str = "N/A"
    citation_count: int = 0
    url: str = ""
    source: str = "unknown"
    abstract: Optional[str] = None


class AnalyzeOptions(BaseModel):
    """Analyze command options."""

    paper_path: Path
    output_path: Optional[Path] = None
    rounds: int = 3
    force_reconvert: bool = False
    verbose: bool = False


class SearchOptions(BaseModel):
    """Search command options."""

    query: str
    limit: int = 10
    source: SearchSource = "both"
    verbose: bool = False
    raw_request: Optional[str] = None
    requested_limit: Optional[int] = None
    candidate_limit: Optional[int] = None
    interactive: bool = True
    limit_overridden: bool = False
    source_overridden: bool = False


class SearchClarificationOption(BaseModel):
    """One selectable option for an ambiguous request field."""

    value: str
    label: str


class SearchClarification(BaseModel):
    """A clarification item that requires user confirmation."""

    field: str
    prompt: str
    options: list[SearchClarificationOption] = Field(default_factory=list)


class SearchFilters(BaseModel):
    """Structured search constraints extracted from the user request."""

    keywords: list[str] = Field(default_factory=list)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    target_count: Optional[int] = None
    venue_policy: Optional[str] = None
    source_preference: Optional[SearchSource] = None


class SearchParseResult(BaseModel):
    """Structured parse output for the search agent."""

    raw_request: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    ambiguities: list[SearchClarification] = Field(default_factory=list)
    parser: str = "heuristic"
    parser_notes: list[str] = Field(default_factory=list)


class SearchAgentResult(BaseModel):
    """Search-agent output exposed to the CLI."""

    results: list[SearchResult] = Field(default_factory=list)
    expanded_queries: list[str] = Field(default_factory=list)
    source_stats: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace_dir: str
    parse_result: SearchParseResult
    retrieved_count: int = 0
    filtered_count: int = 0
    candidate_limit: int = 0


class AnalyzeWorkflowResult(BaseModel):
    """Analyze workflow output exposed to the CLI."""

    report_markdown: str
    report_title: str
    from_cache: bool = False
    paper_id: str
    saved_report_path: Optional[str] = None
    supplementary_search_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class SearchWorkflowResult(BaseModel):
    """Search workflow output exposed to the CLI."""

    results: list[SearchResult] = Field(default_factory=list)
    expanded_queries: list[str] = Field(default_factory=list)
    source_stats: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
