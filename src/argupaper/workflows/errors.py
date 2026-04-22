"""Workflow-level errors surfaced to the CLI."""


class WorkflowError(RuntimeError):
    """Base class for workflow errors."""


class ConfigurationError(WorkflowError):
    """Raised when required configuration is missing or invalid."""


class InputValidationError(WorkflowError):
    """Raised when CLI input is invalid."""


class ExternalServiceError(WorkflowError):
    """Raised when an external service fails."""


class WorkflowExecutionError(WorkflowError):
    """Raised when an internal workflow step fails."""
