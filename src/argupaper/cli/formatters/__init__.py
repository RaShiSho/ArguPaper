"""Output formatters for CLI display."""

from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from argupaper.workflows.models import AnalyzeWorkflowResult, SearchAgentResult, SearchWorkflowResult


console = Console(width=160)

ERROR_HINTS = {
    "ConfigurationError": "Check the required environment variables in .env.example and export them before retrying.",
    "InputValidationError": "Check the command arguments and run the command again.",
    "ExternalServiceError": "Check network access, API credentials, and the selected external source.",
    "WorkflowExecutionError": "Review the visible warning or error above, then retry with --verbose if available.",
    "FileNotFoundError": "Check that the path exists and is accessible from the current working directory.",
    "ValueError": "Check the command arguments and configuration values.",
}


def format_search_results(
    result: SearchWorkflowResult | SearchAgentResult | list[dict[str, Any]]
) -> None:
    """Format and display search results as a table."""

    results = result.results if hasattr(result, "results") else result
    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = Table(
        title="Search Results",
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="white")
    table.add_column("Authors", style="dim")
    table.add_column("Year", justify="center")
    table.add_column("Venue", style="green")
    table.add_column("Citations", justify="right")
    table.add_column("URL", style="blue")

    for i, result in enumerate(results, 1):
        row = result.model_dump() if hasattr(result, "model_dump") else result
        authors = ", ".join(row.get("authors", [])[:2])
        if len(row.get("authors", [])) > 2:
            authors += " et al."

        table.add_row(
            str(i),
            row.get("title", "Unknown"),
            authors,
            str(row.get("year", "N/A")),
            row.get("venue", "N/A"),
            str(row.get("citation_count", 0)),
            row.get("url", ""),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} result(s)[/dim]")


def format_error(error: Exception) -> Panel:
    """Format an exception as a styled error panel."""

    error_type = type(error).__name__
    error_msg = str(error)
    hint = ERROR_HINTS.get(error_type)
    content = f"[bold red]{error_type}[/bold red]: {error_msg or 'No details available.'}"
    if hint:
        content += f"\n\n[bold]Next step[/bold]: {hint}"

    return Panel(
        content,
        title="[bold]Error[/bold]",
        border_style="red",
        expand=False,
    )


def format_success(message: str) -> Panel:
    """Format a success message."""

    return Panel(
        f"[bold green]{message}[/bold green]",
        title="[bold]Success[/bold]",
        border_style="green",
        expand=False,
    )


def format_warning(message: str) -> Panel:
    """Format a warning message."""

    return Panel(
        f"[bold yellow]{message}[/bold yellow]",
        title="[bold]Warning[/bold]",
        border_style="yellow",
        expand=False,
    )


def format_info(message: str) -> Panel:
    """Format an info message."""

    return Panel(
        f"[bold blue]{message}[/bold blue]",
        title="[bold]Info[/bold]",
        border_style="blue",
        expand=False,
    )


def format_warnings(warnings: list[str]) -> None:
    """Display workflow warnings."""

    for warning in warnings:
        console.print(format_warning(warning))


def format_analyze_summary(result: AnalyzeWorkflowResult) -> None:
    """Display concise debate workflow metadata."""

    summary = Text()
    summary.append(f"Paper ID: {result.paper_id}\n", style="cyan")
    summary.append(f"From cache: {'yes' if result.from_cache else 'no'}\n", style="cyan")
    summary.append(
        f"Supplementary retrieval: {'used' if result.supplementary_search_used else 'not used'}",
        style="cyan",
    )
    console.print(Panel(summary, title="[bold]Debate Summary[/bold]", expand=False))


def format_paper_records(records: list[dict[str, Any]]) -> None:
    """Display saved paper records as a table."""

    if not records:
        console.print("[dim]No saved paper records found.[/dim]")
        return

    table = Table(
        title="Saved Papers",
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Paper ID", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Title", style="white")
    table.add_column("Source", style="dim")
    table.add_column("Updated", style="green")

    for index, record in enumerate(records, start=1):
        table.add_row(
            str(index),
            str(record.get("paper_id", "N/A")),
            str(record.get("library_status", "analyzed")),
            str(record.get("title", "Untitled")),
            str(record.get("source", "N/A")),
            str(record.get("updated_at", "N/A")),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(records)} saved paper record(s)[/dim]")


def format_paper_detail(record: dict[str, Any]) -> None:
    """Display one saved paper record."""

    metadata = record.get("metadata", {})
    summary = Text()
    summary.append(f"Paper ID: {metadata.get('paper_id', 'N/A')}\n", style="cyan")
    summary.append(f"Status: {metadata.get('library_status', 'analyzed')}\n", style="magenta")
    summary.append(f"Title: {metadata.get('title', 'Untitled')}\n", style="white")
    summary.append(f"Source: {metadata.get('source', 'N/A')}\n", style="dim")
    summary.append(f"From cache: {'yes' if metadata.get('from_cache') else 'no'}\n", style="cyan")
    summary.append(f"Updated: {metadata.get('updated_at', 'N/A')}", style="green")
    console.print(Panel(summary, title="[bold]Saved Paper[/bold]", expand=False))

    abstract = record.get("abstract", {})
    if abstract:
        abstract_text = Text()
        for key in ("problem", "method", "experiment", "conclusion"):
            value = str(abstract.get(key, "")).strip()
            if value:
                abstract_text.append(f"{key.title()}: ", style="bold cyan")
                abstract_text.append(f"{value}\n")
        console.print(Panel(abstract_text, title="[bold]Structured Summary[/bold]", expand=False))


def render_markdown(markdown: str) -> Markdown:
    """Wrap markdown for Rich rendering."""

    return Markdown(markdown)
