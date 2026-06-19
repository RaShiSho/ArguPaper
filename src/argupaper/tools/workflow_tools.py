"""Workflow-backed tool wrappers for Agents."""

from __future__ import annotations

from collections.abc import Callable

from argupaper.config import Config
from argupaper.tools.registry import ToolRegistry
from argupaper.tools.schemas import DebatePaperArgs, SearchPapersArgs, ToolResult
from argupaper.workflows import AnalyzeOptions, AnalyzeWorkflow, SearchOptions
from argupaper.workflows.search import InteractiveSearchWorkflow

ProgressCallback = Callable[[str], None] | None


def register_workflow_tools(
    registry: ToolRegistry,
    config: Config,
    *,
    progress_callback: ProgressCallback = None,
) -> None:
    """Register workflow-backed tools."""

    toolbox = WorkflowToolbox(config, progress_callback=progress_callback)
    registry.register(
        "debate_paper",
        "Run multi-agent debate analysis for a selected or explicit paper id using the existing workflow.",
        toolbox.debate_paper,
        args_schema=DebatePaperArgs,
    )
    registry.register(
        "search_papers",
        "Search external academic sources with the existing search workflow.",
        toolbox.search_papers,
        args_schema=SearchPapersArgs,
    )


class WorkflowToolbox:
    """Existing workflows exposed as reusable Agent tools."""

    def __init__(self, config: Config, *, progress_callback: ProgressCallback = None) -> None:
        self.config = config
        self.progress_callback = progress_callback

    async def debate_paper(self, paper_id: str | None = None, rounds: int = 3) -> ToolResult:
        """Run the multi-agent debate analysis workflow for a converted paper."""

        if not paper_id:
            return ToolResult(
                tool="debate_paper",
                ok=False,
                summary="No paper is selected. Use /use <paper-id-or-name> first.",
                data={},
            )
        self._progress(f"Running multi-agent debate analysis for {paper_id}...")
        workflow = AnalyzeWorkflow(self.config)
        result = await workflow.run(
            AnalyzeOptions(paper_name=paper_id, rounds=rounds),
            progress_callback=self._progress,
        )
        return ToolResult(
            tool="debate_paper",
            ok=True,
            summary=f"Debate analysis complete for {result.paper_id}: {result.report_title}",
            data={
                "paper_id": result.paper_id,
                "report_title": result.report_title,
                "from_cache": result.from_cache,
                "supplementary_search_used": result.supplementary_search_used,
                "warnings": result.warnings,
                "report_excerpt": self._truncate(result.report_markdown, 3000),
            },
        )

    async def search_papers(self, query: str, limit: int = 10, source: str = "both") -> ToolResult:
        """Run the existing natural-language search workflow."""

        self._progress(f"Searching papers: {query}...")
        workflow = InteractiveSearchWorkflow(self.config)
        result = await workflow.run(
            SearchOptions(
                query=query,
                limit=limit,
                source=source,  # type: ignore[arg-type]
                raw_request=query,
                requested_limit=limit,
                interactive=False,
                limit_overridden=True,
                source_overridden=True,
            ),
            progress_callback=self._progress,
        )
        records = [item.model_dump() for item in result.results]
        return ToolResult(
            tool="search_papers",
            ok=True,
            summary=f"Found {len(records)} paper(s) for: {query}",
            data={
                "results": records,
                "warnings": result.warnings,
                "trace_dir": result.trace_dir,
                "retrieved_count": result.retrieved_count,
                "filtered_count": result.filtered_count,
            },
        )

    def _progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)

    def _truncate(self, text: str, limit: int) -> str:
        normalized = text.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."


__all__ = ["WorkflowToolbox", "register_workflow_tools"]
