"""Run PaperCourtGraph against SciFact claims."""

from __future__ import annotations

from typing import Any

from argupaper.agents.court import PaperCourtGraph
from argupaper.config import Config
from argupaper.workflows.models import SearchOptions, SearchWorkflowResult

from scifact_court_eval.models import ScifactClaim
from scifact_court_eval.retriever import ScifactRAGRetriever


class EmptySearchWorkflow:
    """Disable external related-work search during SciFact evaluation."""

    async def run(self, options: SearchOptions) -> SearchWorkflowResult:
        """Return no external papers so metrics focus on SciFact evidence."""

        return SearchWorkflowResult(results=[], expanded_queries=[], source_stats={}, warnings=[])


class ScifactCourtRunner:
    """Run the existing court graph using the SciFact retriever adapter."""

    def __init__(
        self,
        config: Config,
        *,
        top_k: int,
        max_rounds: int,
        collection: str,
    ) -> None:
        self.config = config.model_copy(
            update={
                "rag": config.rag.model_copy(
                    update={
                        "enabled": True,
                        "top_k": top_k,
                    }
                )
            }
        )
        self.top_k = top_k
        self.max_rounds = max_rounds
        self.collection = collection

    async def run_claim(self, claim: ScifactClaim) -> dict[str, Any]:
        """Run court for one SciFact claim and return a serializable report."""

        retriever = ScifactRAGRetriever(
            self.config,
            top_k=self.top_k,
            collection=self.collection,
        )
        graph = PaperCourtGraph(
            self.config,
            rag_retriever_factory=lambda: retriever,
            search_workflow_factory=lambda: EmptySearchWorkflow(),  # type: ignore[arg-type]
        )
        report = await graph.ainvoke(
            paper_id=f"scifact-claim-{claim.claim_id}",
            title=f"SciFact Claim {claim.claim_id}",
            markdown=self._synthetic_markdown(claim),
            max_rounds=self.max_rounds,
        )
        return report.model_dump()

    def _synthetic_markdown(self, claim: ScifactClaim) -> str:
        return (
            f"# SciFact Claim {claim.claim_id}\n\n"
            "## Abstract\n\n"
            f"We show that {claim.text}\n\n"
            "## Notes\n\n"
            "This synthetic paper is used only to route one SciFact claim through the court graph. "
            "All substantive evidence must come from retrieved SciFact corpus chunks.\n"
        )

