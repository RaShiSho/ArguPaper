"""Search CLI command."""

import sys
from pathlib import Path

import typer
from click import IntRange
from click.core import ParameterSource
from rich.progress import Progress, SpinnerColumn, TextColumn

from argupaper.cli.commands.common import SPINNER_NAME, build_search_workflow, console
from argupaper.cli.formatters import (
    format_error,
    format_info,
    format_search_results,
    format_success,
    format_warnings,
)
from argupaper.workflows import ExternalServiceError, InputValidationError, SearchOptions
from argupaper.workflows.models import SearchClarification
from argupaper.workflows.search import InteractiveSearchWorkflow, SearchClarificationResponse


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

        limit_overridden = ctx.get_parameter_source("limit") == ParameterSource.COMMANDLINE
        source_overridden = ctx.get_parameter_source("source") == ParameterSource.COMMANDLINE
        _run_search(
            workflow=build_search_workflow(),
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


def _run_search(workflow: InteractiveSearchWorkflow, options: SearchOptions) -> None:
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


__all__ = ["search"]

