"""CLI commands for ArguPaper."""

import asyncio
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
    format_paper_detail,
    format_paper_records,
    format_search_results,
    format_success,
    format_warnings,
    render_markdown,
)
from argupaper.agents.search import SearchClarificationResponse
from argupaper.config import load_config
from argupaper.memory.paper_store import PaperStore
from argupaper.workflows import (
    AnalyzeOptions,
    AnalyzeWorkflow,
    ExternalServiceError,
    InputValidationError,
    SearchOptions,
)
from argupaper.workflows.models import SearchClarification
from argupaper.workflows.search_agent import SearchAgentWorkflow


console = Console()
SPINNER_NAME = "line"
DEFAULT_OUTPUT_DIR = Path("output")


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


def resolve_analyze_output_path(output: str | None) -> Path | None:
    """Resolve analyze output paths.

    A bare filename such as "1.md" is saved under output/ by default. Explicit
    paths like "reports/1.md", ".\\1.md", or absolute paths keep their meaning.
    """

    if output is None:
        return None

    output_path = Path(output)
    has_explicit_path = any(separator in output for separator in ("/", "\\"))
    if output_path.is_absolute() or has_explicit_path:
        return output_path
    return DEFAULT_OUTPUT_DIR / output_path


def resolve_auto_report_path(paper_path: Path) -> Path:
    """Build the default report path from the input paper filename."""

    return DEFAULT_OUTPUT_DIR / f"{paper_path.stem}.md"


def build_paper_store() -> PaperStore:
    """Construct the default local paper store."""

    config = load_config(require_pdf_api_key=False)
    return PaperStore(storage_path=config.paper_storage_path)


def analyze(
    paper: str = typer.Argument(..., help="Path to PDF file or URL"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    save_report: bool = typer.Option(
        False,
        "--save-report",
        help="Save report markdown to output/<paper-filename>.md when --output is not set",
    ),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of debate rounds"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reconvert even if cached"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Analyze a research paper with multi-agent debate."""

    try:
        if paper.startswith(("http://", "https://")):
            raise InputValidationError(
                "URL analysis is not part of the MVP CLI. Please use a local PDF path."
            )
        if rounds <= 0:
            raise InputValidationError("--rounds must be greater than 0.")

        paper_path = Path(paper)
        if not paper_path.exists():
            raise InputValidationError(f"PDF file not found: {paper_path}")
        if paper_path.suffix.lower() != ".pdf":
            raise InputValidationError("Input must be a .pdf file.")

        workflow = build_analyze_workflow()
        output_path = resolve_analyze_output_path(output)
        if output_path is None and save_report:
            output_path = resolve_auto_report_path(paper_path)

        _run_analyze(
            workflow=workflow,
            options=AnalyzeOptions(
                paper_path=paper_path,
                output_path=output_path,
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
        SpinnerColumn(SPINNER_NAME),
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
        options.output_path.parent.mkdir(parents=True, exist_ok=True)
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
        help="Search source: semantic_scholar, arxiv, google_scholar, serpapi, or both",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Search for academic papers."""

    try:
        if limit <= 0:
            raise InputValidationError("--limit must be greater than 0.")
        if source not in {"semantic_scholar", "arxiv", "google_scholar", "serpapi", "both"}:
            raise InputValidationError(
                "--source must be one of: semantic_scholar, arxiv, google_scholar, serpapi, both."
            )

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
        SpinnerColumn(SPINNER_NAME),
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
        raise ExternalServiceError("All search sources failed.")

    console.print(format_success("Search complete"))
    if not result.results:
        format_warnings(["Search completed but returned no results. Try a broader query or another source."])
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


def papers(
    paper_id: Optional[str] = typer.Argument(
        None,
        help="Saved paper ID or unique hash prefix. Omit to list saved records.",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Search saved records by title, source, paper ID, or structured summary.",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum records to display"),
    report: bool = typer.Option(False, "--report", help="Render the saved report for a paper"),
    markdown: bool = typer.Option(False, "--markdown", help="Render the saved paper markdown"),
) -> None:
    """Inspect locally saved paper analysis records."""

    try:
        if paper_id and query:
            raise InputValidationError("Use either a paper_id argument or --query, not both.")
        if limit <= 0:
            raise InputValidationError("--limit must be greater than 0.")

        store = build_paper_store()
        if paper_id:
            record = asyncio.run(store.get_paper(paper_id))
            if record is None:
                raise InputValidationError(f"Saved paper record not found: {paper_id}")
            format_paper_detail(record)
            if report:
                saved_report = str(record.get("report", "")).strip()
                if saved_report:
                    console.print(render_markdown(saved_report))
                else:
                    console.print("[dim]No saved report found for this paper.[/dim]")
            if markdown:
                saved_markdown = str(record.get("markdown", "")).strip()
                if saved_markdown:
                    console.print(render_markdown(saved_markdown))
                else:
                    console.print("[dim]No saved markdown found for this paper.[/dim]")
            return

        records = (
            asyncio.run(store.search_papers(query))
            if query
            else asyncio.run(store.list_papers())
        )
        format_paper_records(records[:limit])
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


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
