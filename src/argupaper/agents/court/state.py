"""State schema for the paper court LangGraph subgraph."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from argupaper.domain.court import Argument, Claim, ClaimVerdict, CriticalClaimReport, Dispute, Evidence


class PaperCourtState(TypedDict):
    """Mutable state passed between court sub-agents."""

    paper_id: str
    title: str
    markdown: str
    max_rounds: int
    current_round: int
    claims: list[Claim]
    evidence: list[Evidence]
    challenges: list[Argument]
    defenses: list[Argument]
    disputes: list[Dispute]
    verdicts: list[ClaimVerdict]
    used_attack_keys: list[str]
    new_challenge_count: int
    stop_reason: str
    warnings: list[str]
    report: CriticalClaimReport | None
    route: NotRequired[str]
    external_results: NotRequired[list[dict[str, Any]]]

