"""Analyze CLI command."""

from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from argupaper.cli.commands.common import (
    SPINNER_NAME,
    build_analyze_workflow,
    console,
    resolve_analyze_output_path,
    resolve_auto_report_path,
)
from argupaper.cli.formatters import (
    format_analyze_summary,
    format_error,
    format_info,
    format_success,
    format_warnings,
    render_markdown,
)
from argupaper.workflows import AnalyzeOptions, AnalyzeWorkflow, InputValidationError


def analyze(
    paper: str = typer.Argument(..., help="Converted paper name, cache key, or legacy local PDF path"),
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
                "URL analysis is not part of the MVP CLI. Please use a converted paper name or local PDF path."
            )
        if rounds <= 0:
            raise InputValidationError("--rounds must be greater than 0.")

        paper_path = Path(paper)
        analyze_options: dict[str, object]
        if paper_path.exists():
            if paper_path.suffix.lower() != ".pdf":
                raise InputValidationError("Input must be a converted paper name or a .pdf file.")
            analyze_options = {"paper_path": paper_path}
        else:
            analyze_options = {"paper_name": paper}

        output_path = resolve_analyze_output_path(output)
        if output_path is None and save_report:
            output_path = resolve_auto_report_path(Path(paper))

        _run_analyze(
            workflow=build_analyze_workflow(),
            options=AnalyzeOptions(
                **analyze_options,
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


__all__ = ["analyze"]

