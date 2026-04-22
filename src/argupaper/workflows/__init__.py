"""Workflow entrypoints used by the CLI."""

from argupaper.workflows.analyze_paper import AnalyzeWorkflow
from argupaper.workflows.errors import (
    ConfigurationError,
    ExternalServiceError,
    InputValidationError,
    WorkflowError,
    WorkflowExecutionError,
)
from argupaper.workflows.models import (
    AnalyzeOptions,
    AnalyzeWorkflowResult,
    SearchAgentResult,
    SearchClarification,
    SearchFilters,
    SearchParseResult,
    SearchOptions,
    SearchResult,
    SearchWorkflowResult,
)
from argupaper.workflows.search_papers import SearchWorkflow

__all__ = [
    "AnalyzeOptions",
    "AnalyzeWorkflow",
    "AnalyzeWorkflowResult",
    "ConfigurationError",
    "ExternalServiceError",
    "InputValidationError",
    "SearchAgentResult",
    "SearchClarification",
    "SearchFilters",
    "SearchOptions",
    "SearchParseResult",
    "SearchResult",
    "SearchWorkflow",
    "SearchWorkflowResult",
    "WorkflowError",
    "WorkflowExecutionError",
]
