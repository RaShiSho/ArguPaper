"""Options for the Adversarial Paper Court workflow."""

from pathlib import Path

from pydantic import BaseModel


class CourtOptions(BaseModel):
    """CLI/tool options for claim-level adversarial review."""

    paper_id: str
    output_path: Path | None = None
    max_rounds: int = 2
    verbose: bool = False

