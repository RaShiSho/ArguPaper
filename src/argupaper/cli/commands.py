"""CLI commands for ArguPaper."""

import sys
from pathlib import Path
from typing import Optional

import typer
from click import IntRange
from click.core import ParameterSource
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from argupaper.cli.formatters import (
    format_analyze_summary,
    format_error,
    format_info,
    format_search_results,
    format_success,
    format_warnings,
    render_markdown,
)
from argupaper.agents.search import SearchClarificationResponse
from argupaper.config import load_config
from argupaper.workflows import (
    AnalyzeOptions,
    AnalyzeWorkflow,
    SearchOptions,
)
from argupaper.workflows.models import SearchClarification
from argupaper.workflows.search_agent import SearchAgentWorkflow


console = Console()


def build_analyze_workflow() -> AnalyzeWorkflow:
    """Construct the default analyze workflow."""

    config = load_config(require_pdf_api_key=True)
    return AnalyzeWorkflow(config)


def build_search_agent_workflow() -> SearchAgentWorkflow:
    """Construct the default search-agent workflow."""

    config = load_config(require_pdf_api_key=False)
    return SearchAgentWorkflow(config)


def build_search_workflow() -> SearchAgentWorkflow:
    """Backward-compatible alias for the search-agent workflow builder."""

    return build_search_agent_workflow()


def analyze(
    paper: str = typer.Argument(..., help="Path to PDF file or URL"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of debate rounds"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reconvert even if cached"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Analyze a research paper with multi-agent debate."""

    try:
        if paper.startswith(("http://", "https://")):
            raise ValueError(
                "URL analysis is not part of the MVP CLI. Please use a local PDF path."
            )
        if rounds <= 0:
            raise ValueError("--rounds must be greater than 0.")

        paper_path = Path(paper)
        if not paper_path.exists():
            raise FileNotFoundError(f"PDF file not found: {paper_path}")
        if paper_path.suffix.lower() != ".pdf":
            raise ValueError("Input must be a .pdf file.")

        workflow = build_analyze_workflow()
        _run_analyze(
            workflow=workflow,
            options=AnalyzeOptions(
                paper_path=paper_path,
                output_path=Path(output) if output else None,
                rounds=rounds,
                force_reconvert=force,
                verbose=verbose,
            ),
        )
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _run_analyze(workflow: AnalyzeWorkflow, options: AnalyzeOptions) -> None:
    """Run the analysis workflow synchronously."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Preparing analysis...", total=None)

        def progress_callback(message: str) -> None:
            progress.update(task, description=f"[cyan]{message}")

        result = workflow.run_sync(options, progress_callback)
        progress.update(task, completed=True)

    console.print(format_success("Analysis complete"))
    if result.from_cache:
        console.print("[dim]Result loaded from cache (use --force to reconvert)[/dim]\n")

    format_analyze_summary(result)
    if result.warnings:
        format_warnings(result.warnings)

    if options.verbose:
        console.print(format_info(f"Report title: {result.report_title}"))

    if options.output_path:
        options.output_path.write_text(result.report_markdown, encoding="utf-8")
        console.print(f"[dim]Report saved to: {options.output_path.absolute()}[/dim]")

    console.print(render_markdown(result.report_markdown))


def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results"),
    source: str = typer.Option(
        "both",
        "--source",
        "-s",
        help="Search source: semantic_scholar, arxiv, or both",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Search for academic papers."""

    try:
        if limit <= 0:
            raise ValueError("--limit must be greater than 0.")
        if source not in {"semantic_scholar", "arxiv", "both"}:
            raise ValueError("--source must be one of: semantic_scholar, arxiv, both.")

        workflow = build_search_agent_workflow()
        limit_overridden = ctx.get_parameter_source("limit") == ParameterSource.COMMANDLINE
        source_overridden = ctx.get_parameter_source("source") == ParameterSource.COMMANDLINE
        _run_search(
            workflow=workflow,
            options=SearchOptions(
                query=query,
                limit=limit,
                source=source,
                verbose=verbose,
                raw_request=query,
                requested_limit=limit if limit_overridden else None,
                interactive=sys.stdin.isatty() and sys.stdout.isatty(),
                limit_overridden=limit_overridden,
                source_overridden=source_overridden,
            ),
        )
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _run_search(workflow: SearchAgentWorkflow, options: SearchOptions) -> None:
    """Run paper search."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Searching: {options.query}...", total=None)

        def progress_callback(message: str) -> None:
            progress.update(task, description=f"[cyan]{message}")

        result = workflow.run_sync(
            options,
            progress_callback,
            clarification_callback=_resolve_search_clarification if options.interactive else None,
        )
        progress.update(task, completed=True)

    if result.warnings:
        format_warnings(result.warnings)

    if (
        not result.results
        and result.retrieved_count == 0
        and any("search failed" in warning.lower() for warning in result.warnings)
    ):
        raise RuntimeError("All search sources failed.")

    console.print(format_success("Search complete"))
    if options.verbose:
        console.print(format_info(f"Parser: {result.parse_result.parser}"))
        console.print(
            format_info(f"Parsed keywords: {', '.join(result.parse_result.filters.keywords) or 'N/A'}")
        )
        console.print(format_info(f"Expanded queries: {', '.join(result.expanded_queries)}"))
        console.print(format_info(f"Source stats: {result.source_stats}"))
        console.print(
            format_info(
                "Filter summary: "
                f"retrieved={result.retrieved_count}, filtered={result.filtered_count}, "
                f"candidate_limit={result.candidate_limit}"
            )
        )

    format_search_results(result)
    console.print(f"[dim]Trace saved to: {Path(result.trace_dir).absolute()}[/dim]")


def _resolve_search_clarification(item: SearchClarification) -> SearchClarificationResponse:
    """Interactively resolve one ambiguous search filter."""

    console.print(format_info(item.prompt))
    for index, option in enumerate(item.options, start=1):
        console.print(f"[dim]{index}. {option.label}[/dim]")

    choice = typer.prompt(
        "Select an option",
        type=IntRange(1, len(item.options)),
    )
    selected = item.options[choice - 1]
    return SearchClarificationResponse(
        field=item.field,
        selected_value=selected.value,
        selected_label=selected.label,
    )


def get_app() -> typer.Typer:
    """Get the Typer app instance for programmatic use."""

    from argupaper.cli import app

    return app
