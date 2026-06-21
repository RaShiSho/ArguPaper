"""Workflow wrapper for the Adversarial Paper Court subgraph."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from argupaper.agents.court import build_paper_court_graph
from argupaper.config import Config
from argupaper.memory.paper_store import PaperStore
from argupaper.workflows.court.markdown import render_critical_claim_report
from argupaper.workflows.court.options import CourtOptions
from argupaper.workflows.court.result import CourtWorkflowResult
from argupaper.workflows.errors import InputValidationError

ProgressCallback = Callable[[str], None] | None


class CourtWorkflow:
    """Run claim-level adversarial review for one PaperStore record."""

    def __init__(
        self,
        config: Config,
        *,
        paper_store: PaperStore | None = None,
    ) -> None:
        self.config = config
        self.paper_store = paper_store or PaperStore(storage_path=config.paper_storage_path)

    async def run(
        self,
        options: CourtOptions,
        progress_callback: ProgressCallback = None,
    ) -> CourtWorkflowResult:
        """Run the paper court workflow."""

        if not options.paper_id.strip():
            raise InputValidationError("paper_id is required.")
        if options.max_rounds <= 0:
            raise InputValidationError("max_rounds must be greater than 0.")

        if progress_callback:
            progress_callback(f"Loading PaperStore record: {options.paper_id}...")
        record = await self.paper_store.get_paper(options.paper_id)
        if record is None:
            raise InputValidationError(f"Saved paper record not found: {options.paper_id}")

        metadata = dict(record.get("metadata", {}))
        resolved_paper_id = str(metadata.get("paper_id", options.paper_id))
        title = str(metadata.get("title", "Untitled"))
        markdown = str(record.get("markdown", ""))
        if not markdown.strip():
            raise InputValidationError(f"Saved paper markdown not found: {resolved_paper_id}")

        graph = build_paper_court_graph(self.config, progress_callback=progress_callback)
        report = await graph.ainvoke(
            paper_id=resolved_paper_id,
            title=title,
            markdown=markdown,
            max_rounds=options.max_rounds,
        )
        report_markdown = render_critical_claim_report(report)

        saved_report_path: str | None = None
        if options.output_path is not None:
            options.output_path.parent.mkdir(parents=True, exist_ok=True)
            options.output_path.write_text(report_markdown, encoding="utf-8")
            saved_report_path = str(options.output_path)

        return CourtWorkflowResult(
            paper_id=resolved_paper_id,
            report_title=f"Critical Claim Report: {title}",
            report_markdown=report_markdown,
            structured_report=report,
            saved_report_path=saved_report_path,
            warnings=report.warnings,
        )

    def run_sync(
        self,
        options: CourtOptions,
        progress_callback: ProgressCallback = None,
    ) -> CourtWorkflowResult:
        """Synchronous wrapper used by Typer commands."""

        return asyncio.run(self.run(options, progress_callback))

