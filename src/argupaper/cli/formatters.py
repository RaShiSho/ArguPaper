"""Output formatters for CLI display."""

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console()


def format_search_results(results: list[dict[str, Any]]) -> None:
    """Format and display search results as a table."""
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

    for i, result in enumerate(results, 1):
        authors = ", ".join(result.get("authors", [])[:2])
        if len(result.get("authors", [])) > 2:
            authors += " et al."

        table.add_row(
            str(i),
            result.get("title", "Unknown"),
            authors,
            str(result.get("year", "N/A")),
            result.get("venue", "N/A"),
            str(result.get("citation_count", 0)),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} result(s)[/dim]")


def format_error(error: Exception) -> Panel:
    """Format an exception as a styled error panel."""
    error_type = type(error).__name__
    error_msg = str(error)

    content = f"[bold red]{error_type}[/bold red]: {error_msg}"

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
