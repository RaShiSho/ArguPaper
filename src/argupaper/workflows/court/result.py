"""Result model for the Adversarial Paper Court workflow."""

from pydantic import BaseModel, Field

from argupaper.domain.court import CriticalClaimReport


class CourtWorkflowResult(BaseModel):
    """Court workflow output exposed to CLI and Agent tools."""

    paper_id: str
    report_title: str
    report_markdown: str
    structured_report: CriticalClaimReport
    saved_report_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
