"""Workflow for natural-language search requests."""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from argupaper.workflows.search.parser import SearchRequestParser, SearchRequestRunner, SearchTraceStore
from argupaper.config import Config
from argupaper.services.llm import LLMRouter
from argupaper.workflows.models import SearchAgentResult, SearchOptions
from argupaper.workflows.search.workflow import SearchWorkflow

ProgressCallback = Optional[Callable[[str], None]]


class InteractiveSearchWorkflow:
    """High-level workflow used by the CLI search command."""

    def __init__(
        self,
        config: Config,
        *,
        search_workflow: Optional[SearchWorkflow] = None,
        llm_router: Optional[LLMRouter] = None,
    ):
        self.config = config
        self.llm_router = llm_router or LLMRouter(config.model)
        self.search_workflow = search_workflow or SearchWorkflow(config)
        self.runner = SearchRequestRunner(
            config=config,
            parser=SearchRequestParser(config, llm_router=self.llm_router),
            trace_store=SearchTraceStore(config.search_agent.trace_path),
        )

    async def run(
        self,
        options: SearchOptions,
        progress_callback: ProgressCallback = None,
        clarification_callback=None,
    ) -> SearchAgentResult:
        """Run the natural-language search workflow."""

        try:
            return await self.runner.run(
                options,
                search_runner=lambda search_options: self.search_workflow.run(
                    search_options,
                    progress_callback,
                ),
                clarification_callback=clarification_callback,
                progress_callback=progress_callback,
            )
        finally:
            await self.llm_router.close()

    def run_sync(
        self,
        options: SearchOptions,
        progress_callback: ProgressCallback = None,
        clarification_callback=None,
    ) -> SearchAgentResult:
        """Synchronous wrapper used by Typer commands."""

        return asyncio.run(self.run(options, progress_callback, clarification_callback))

