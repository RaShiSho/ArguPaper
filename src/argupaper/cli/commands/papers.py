"""Papers CLI command."""

import asyncio
from typing import Optional

import typer

from argupaper.cli.commands.common import build_papers_workflow, console
from argupaper.cli.formatters import (
    format_error,
    format_paper_detail,
    format_paper_records,
    render_markdown,
)
from argupaper.workflows.papers import PapersOptions


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
    """Inspect locally saved paper library records."""

    try:
        result = asyncio.run(
            build_papers_workflow().run(
                PapersOptions(
                    paper_id=paper_id,
                    query=query,
                    limit=limit,
                )
            )
        )
        if result.record is not None:
            record = result.record
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

        format_paper_records(result.records)
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


__all__ = ["papers"]
