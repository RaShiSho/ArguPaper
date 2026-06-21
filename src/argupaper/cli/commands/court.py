"""Adversarial Paper Court CLI command."""

from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from argupaper.cli.commands.common import SPINNER_NAME, console
from argupaper.cli.formatters import format_error, format_success, format_warnings
from argupaper.config import load_config
from argupaper.workflows import CourtOptions, CourtWorkflow, InputValidationError


def court(
    paper_id: str = typer.Argument(..., help="Saved PaperStore paper id or unique prefix"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output Markdown report path"),
    rounds: int = typer.Option(2, "--rounds", "-r", help="Maximum adversarial debate rounds"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run claim-level adversarial paper court review."""

    try:
        if rounds <= 0:
            raise InputValidationError("--rounds must be greater than 0.")
        output_path = Path(output) if output else None
        workflow = CourtWorkflow(load_config(require_pdf_api_key=False))
        _run_court(
            workflow,
            CourtOptions(
                paper_id=paper_id,
                output_path=output_path,
                max_rounds=rounds,
                verbose=verbose,
            ),
        )
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


def _run_court(workflow: CourtWorkflow, options: CourtOptions) -> None:
    """Run the court workflow synchronously."""

    with Progress(
        SpinnerColumn(SPINNER_NAME),
        TextColumn("[progress.description]{task.description}"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Preparing paper court...", total=None)

        def progress_callback(message: str) -> None:
            progress.update(task, description=f"[cyan]{message}")

        result = workflow.run_sync(options, progress_callback)
        progress.update(task, completed=True)

    console.print(format_success("Paper court review complete"))
    if result.warnings:
        format_warnings(result.warnings)
    if result.saved_report_path:
        console.print(f"[dim]Report saved to: {Path(result.saved_report_path).absolute()}[/dim]")
    if options.verbose:
        console.print(f"[dim]Report title: {result.report_title}[/dim]")
    console.print(_console_safe_text(result.report_markdown))


def _console_safe_text(text: str) -> str:
    """Replace characters that cannot be rendered by the active Windows console."""

    return text.encode("gbk", errors="replace").decode("gbk", errors="replace")


__all__ = ["court"]
