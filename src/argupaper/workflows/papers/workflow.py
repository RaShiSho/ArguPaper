"""Workflow for inspecting saved paper records."""

from argupaper.memory.paper_store import PaperStore
from argupaper.workflows.errors import InputValidationError
from argupaper.workflows.papers.options import PapersOptions
from argupaper.workflows.papers.result import PapersWorkflowResult


class PapersWorkflow:
    """List, search, or load saved paper records."""

    def __init__(self, paper_store: PaperStore):
        self.paper_store = paper_store

    async def run(self, options: PapersOptions) -> PapersWorkflowResult:
        """Run a saved-paper inspection."""

        if options.paper_id and options.query:
            raise InputValidationError("Use either a paper_id argument or --query, not both.")
        if options.limit <= 0:
            raise InputValidationError("--limit must be greater than 0.")

        if options.paper_id:
            record = await self.paper_store.get_paper(options.paper_id)
            if record is None:
                raise InputValidationError(f"Saved paper record not found: {options.paper_id}")
            return PapersWorkflowResult(record=record)

        records = (
            await self.paper_store.search_papers(options.query)
            if options.query
            else await self.paper_store.list_papers()
        )
        return PapersWorkflowResult(records=records[: options.limit])


__all__ = ["PapersWorkflow"]
