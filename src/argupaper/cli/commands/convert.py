"""Convert CLI command."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from argupaper.cli.commands.common import (
    SPINNER_NAME,
    build_convert_workflow,
    console,
    resolve_convert_output_path,
)
from argupaper.cli.formatters import format_error, format_info, format_success
from argupaper.workflows.convert import ConvertOptions
from argupaper.workflows.errors import InputValidationError


def convert(
    pdf: Optional[str] = typer.Argument(None, help="Path to local PDF file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Optional Markdown export path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reconvert even if cached"),
    folder: Optional[str] = typer.Option(
        None,
        "--folder",
        "-d",
        help="Convert all direct PDF files in a folder",
    ),
) -> None:
    """Convert a local PDF to Markdown and store it in the cache."""

    try:
        if pdf and pdf.startswith(("http://", "https://")):
            raise InputValidationError("URL conversion is not supported. Please use a local PDF path.")
        options = ConvertOptions(
            pdf_path=Path(pdf) if pdf else None,
            folder_path=Path(folder) if folder else None,
            output_path=resolve_convert_output_path(output),
            force_reconvert=force,
        )
        workflow = build_convert_workflow()
        with Progress(
            SpinnerColumn(SPINNER_NAME),
            TextColumn("[progress.description]{task.description}"),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Preparing conversion...", total=None)

            def progress_callback(message: str) -> None:
                progress.update(task, description=f"[cyan]{message}")

            def file_event_callback(message: str) -> None:
                progress.console.print(format_info(message))

            result = asyncio.run(workflow.run(options, progress_callback, file_event_callback))
            progress.update(task, completed=True)

        if result.summary is not None:
            summary = result.summary
            console.print(format_success("Folder conversion complete"))
            console.print(format_info(f"Folder: {Path(result.input_path or '').absolute()}"))
            console.print(format_info(f"Total entries: {summary.total_entries}"))
            console.print(format_info(f"Processed PDFs: {summary.processed}"))
            console.print(format_info(f"Succeeded: {summary.success}"))
            console.print(format_info(f"Loaded from cache: {summary.cache_hits}"))
            console.print(format_info(f"Failed: {summary.failed}"))
            console.print(format_info(f"Skipped: {summary.skipped}"))
            if result.run_log_path is not None:
                console.print(f"[dim]Run log: {result.run_log_path.absolute()}[/dim]")
            return

        if result.conversion is None or result.input_path is None:
            raise InputValidationError("Conversion did not produce a result.")
        conversion = result.conversion
        console.print(format_success("Conversion complete"))
        console.print(format_info(f"Original filename: {result.input_path.name}"))
        console.print(format_info(f"Cache key: {conversion.cache_key}"))
        if result.cache_path is not None:
            console.print(format_info(f"Cache path: {result.cache_path}"))
        console.print(format_info(f"Loaded from cache: {'yes' if conversion.from_cache else 'no'}"))
        if result.output_path is not None:
            console.print(f"[dim]Markdown exported to: {result.output_path.absolute()}[/dim]")
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


__all__ = ["convert"]

