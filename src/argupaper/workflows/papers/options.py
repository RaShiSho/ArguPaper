"""Papers workflow options."""

from pydantic import BaseModel


class PapersOptions(BaseModel):
    """Options for inspecting saved paper records."""

    paper_id: str | None = None
    query: str | None = None
    limit: int = 20


__all__ = ["PapersOptions"]

