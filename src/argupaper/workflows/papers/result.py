"""Papers workflow result models."""

from pydantic import BaseModel, Field


class PapersWorkflowResult(BaseModel):
    """Result for saved paper inspection."""

    record: dict | None = None
    records: list[dict] = Field(default_factory=list)


__all__ = ["PapersWorkflowResult"]

