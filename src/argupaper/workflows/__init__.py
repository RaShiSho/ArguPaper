"""Workflow entrypoints used by the CLI."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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
        SearchOptions,
        SearchParseResult,
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


def __getattr__(name: str) -> Any:
    """Resolve workflow exports lazily to avoid package import cycles."""

    if name == "AnalyzeWorkflow":
        from argupaper.workflows.analyze_paper import AnalyzeWorkflow

        return AnalyzeWorkflow
    if name == "SearchWorkflow":
        from argupaper.workflows.search_papers import SearchWorkflow

        return SearchWorkflow
    if name in {
        "ConfigurationError",
        "ExternalServiceError",
        "InputValidationError",
        "WorkflowError",
        "WorkflowExecutionError",
    }:
        from argupaper.workflows import errors

        return getattr(errors, name)
    if name in {
        "AnalyzeOptions",
        "AnalyzeWorkflowResult",
        "SearchAgentResult",
        "SearchClarification",
        "SearchFilters",
        "SearchOptions",
        "SearchParseResult",
        "SearchResult",
        "SearchWorkflowResult",
    }:
        from argupaper.workflows import models

        return getattr(models, name)
    raise AttributeError(f"module 'argupaper.workflows' has no attribute {name!r}")
