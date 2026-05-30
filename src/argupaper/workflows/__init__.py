"""Workflow entrypoints used by CLI, Web, and future tools."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from argupaper.workflows.analyze import AnalyzeWorkflow
    from argupaper.workflows.convert import ConvertOptions, ConvertWorkflow, ConvertWorkflowResult, FolderConvertSummary
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
    from argupaper.workflows.papers import PapersOptions, PapersWorkflow, PapersWorkflowResult
    from argupaper.workflows.search import InteractiveSearchWorkflow, SearchWorkflow

__all__ = [
    "AnalyzeOptions",
    "AnalyzeWorkflow",
    "AnalyzeWorkflowResult",
    "ConfigurationError",
    "ConvertOptions",
    "ConvertWorkflow",
    "ConvertWorkflowResult",
    "ExternalServiceError",
    "FolderConvertSummary",
    "InputValidationError",
    "InteractiveSearchWorkflow",
    "PapersOptions",
    "PapersWorkflow",
    "PapersWorkflowResult",
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
        from argupaper.workflows.analyze import AnalyzeWorkflow

        return AnalyzeWorkflow
    if name in {"ConvertOptions", "ConvertWorkflow", "ConvertWorkflowResult", "FolderConvertSummary"}:
        from argupaper.workflows import convert

        return getattr(convert, name)
    if name in {"PapersOptions", "PapersWorkflow", "PapersWorkflowResult"}:
        from argupaper.workflows import papers

        return getattr(papers, name)
    if name in {"InteractiveSearchWorkflow", "SearchWorkflow"}:
        from argupaper.workflows import search

        return getattr(search, name)
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