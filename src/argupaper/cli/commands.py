"""CLI commands for ArguPaper."""

from pathlib import Path
from typing import Optional

import typer
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
from argupaper.config import load_config
from argupaper.workflows import AnalyzeOptions, AnalyzeWorkflow, SearchOptions, SearchWorkflow


console = Console()


def build_analyze_workflow() -> AnalyzeWorkflow:
    """Construct the default analyze workflow."""

    config = load_config(require_pdf_api_key=True)
    return AnalyzeWorkflow(config)


def build_search_workflow() -> SearchWorkflow:
    """Construct the default search workflow."""

    config = load_config(require_pdf_api_key=False)
    return SearchWorkflow(config)


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

        workflow = build_search_workflow()
        _run_search(
            workflow=workflow,
            options=SearchOptions(
                query=query,
                limit=limit,
                source=source,
                verbose=verbose,
            ),
        )
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _run_search(workflow: SearchWorkflow, options: SearchOptions) -> None:
    """Run paper search."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Searching: {options.query}...", total=None)

        def progress_callback(message: str) -> None:
            progress.update(task, description=f"[cyan]{message}")

        result = workflow.run_sync(options, progress_callback)
        progress.update(task, completed=True)

    if result.warnings:
        format_warnings(result.warnings)

    if not result.results and result.warnings:
        raise RuntimeError("All search sources failed.")

    console.print(format_success("Search complete"))
    if options.verbose:
        console.print(format_info(f"Expanded queries: {', '.join(result.expanded_queries)}"))
        console.print(format_info(f"Source stats: {result.source_stats}"))

    format_search_results(result)


def get_app() -> typer.Typer:
    """Get the Typer app instance for programmatic use."""

    from argupaper.cli import app

    return app
