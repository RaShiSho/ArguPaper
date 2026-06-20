"""RAG CLI command group."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.table import Table

from argupaper.cli.commands.common import build_rag_workflow, console
from argupaper.cli.formatters import format_error, format_success, format_warning
from argupaper.workflows.rag import RAGDeleteOptions, RAGIndexOptions, RAGSearchOptions
from argupaper.workflows.rag.result import (
    RAGDeleteResult,
    RAGIndexResult,
    RAGSearchResult,
    RAGStatusResult,
)

rag_app = typer.Typer(
    name="rag",
    help="Local RAG indexing and search commands.",
    add_completion=False,
)


@rag_app.command("status")
def status() -> None:
    """Show local RAG configuration."""

    try:
        workflow = build_rag_workflow()
        _format_status(workflow.status(progress_callback=_print_progress))
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


@rag_app.command("index")
def index(
    paper_id: str = typer.Argument(..., help="Saved PaperStore paper ID to index."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse and chunk without embedding or Milvus writes."),
) -> None:
    """Index one saved paper into the local RAG vector store."""

    workflow = None
    try:
        workflow = build_rag_workflow()
        result = asyncio.run(
            workflow.index_paper(
                RAGIndexOptions(
                    paper_id=paper_id,
                    dry_run=dry_run,
                ),
                progress_callback=_print_progress,
            )
        )
        _format_index_result(result)
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)
    finally:
        if workflow is not None:
            asyncio.run(workflow.close())


@rag_app.command("delete")
def delete(
    paper_id: str = typer.Argument(..., help="Saved PaperStore paper ID to delete from RAG storage."),
) -> None:
    """Delete one paper from the local RAG vector store."""

    workflow = None
    try:
        workflow = build_rag_workflow()
        result = asyncio.run(
            workflow.delete_paper(
                RAGDeleteOptions(paper_id=paper_id),
                progress_callback=_print_progress,
            )
        )
        _format_delete_result(result)
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)
    finally:
        if workflow is not None:
            asyncio.run(workflow.close())


@rag_app.command("search")
def search(
    content: str = typer.Argument(..., help="Query text for local RAG search."),
    paper_id: Optional[str] = typer.Option(
        None,
        "--paper-id",
        "-p",
        help="Optional PaperStore paper ID. Omit to search the full indexed library.",
    ),
    top_k: Optional[int] = typer.Option(None, "--top-k", "-k", help="Maximum chunks to return."),
    section_type: Optional[str] = typer.Option(
        None,
        "--section-type",
        help="Optional normalized section type such as abstract, method, experiments, or conclusion.",
    ),
    score_threshold: Optional[float] = typer.Option(
        None,
        "--score-threshold",
        help="Minimum similarity score to include.",
    ),
    context_max_chars: int = typer.Option(
        12000,
        "--context-max-chars",
        help="Maximum characters to include in the generated LLM context.",
    ),
    show_context: bool = typer.Option(False, "--context", help="Print the generated LLM context."),
) -> None:
    """Search local RAG chunks. Defaults to full-library search."""

    workflow = None
    try:
        workflow = build_rag_workflow()
        result = asyncio.run(
            workflow.search(
                RAGSearchOptions(
                    content=content,
                    paper_id=paper_id,
                    top_k=top_k,
                    section_type=section_type,
                    score_threshold=score_threshold,
                    context_max_chars=context_max_chars,
                ),
                progress_callback=_print_progress,
            )
        )
        _format_search_result(result, show_context=show_context)
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)
    finally:
        if workflow is not None:
            asyncio.run(workflow.close())


def _format_status(result: RAGStatusResult) -> None:
    table = Table(title="RAG Status", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    rows = {
        "RAG enabled": str(result.rag_enabled),
        "Ollama base URL": result.ollama_base_url,
        "Embedding model": result.ollama_embed_model,
        "Milvus URI": result.milvus_uri,
        "Milvus collection": result.milvus_collection,
        "Top K": str(result.top_k),
        "Chunk size": str(result.chunk_size),
        "Chunk overlap": str(result.chunk_overlap),
        "Include references": str(result.include_references),
        "Vector dimension": str(result.vector_dim),
    }
    for key, value in rows.items():
        table.add_row(key, value)
    console.print(table)
    _print_log_path(result.run_log_path)


def _format_index_result(result: RAGIndexResult) -> None:
    action = "Dry run complete" if result.dry_run else "RAG indexing complete"
    console.print(format_success(action))
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Paper ID", result.paper_id)
    table.add_row("Chunk count", str(result.chunk_count))
    table.add_row("Embedding dim", str(result.embedding_dim) if result.embedding_dim is not None else "N/A")
    table.add_row("Skipped sections", ", ".join(result.skipped_sections) or "None")
    table.add_row("Dry run", str(result.dry_run))
    console.print(table)
    for warning in result.warnings:
        console.print(format_warning(warning))
    _print_log_path(result.run_log_path)


def _format_delete_result(result: RAGDeleteResult) -> None:
    console.print(format_success("RAG delete complete"))
    deleted = str(result.deleted_count) if result.deleted_count is not None else "unknown"
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Paper ID", result.paper_id)
    table.add_row("Deleted chunks", deleted)
    console.print(table)
    for warning in result.warnings:
        console.print(format_warning(warning))
    _print_log_path(result.run_log_path)


def _format_search_result(result: RAGSearchResult, *, show_context: bool) -> None:
    if result.warnings:
        for warning in result.warnings:
            console.print(format_warning(warning))
    if not result.chunks:
        console.print("[dim]No RAG chunks found.[/dim]")
        _print_log_path(result.run_log_path)
        return

    table = Table(title="RAG Search Results", show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Chunk ID", style="cyan")
    table.add_column("Paper", style="magenta")
    table.add_column("Section", style="green")
    table.add_column("Page", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Preview", style="white")
    for index, chunk in enumerate(result.chunks, start=1):
        table.add_row(
            str(index),
            chunk.chunk_id,
            chunk.paper_id,
            chunk.section or chunk.section_type or "unknown",
            _page_label(chunk.page_start, chunk.page_end),
            f"{chunk.score:.4f}",
            _preview(chunk.text),
        )
    console.print(table)
    console.print(f"[dim]Returned {len(result.chunks)} chunk(s).[/dim]")
    if show_context and result.context:
        console.print("\n[bold cyan]Context[/bold cyan]")
        console.print(result.context)
    _print_log_path(result.run_log_path)


def _print_progress(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")


def _print_log_path(log_path: str | None) -> None:
    if log_path:
        console.print(f"[dim]RAG log: {log_path}[/dim]")


def _page_label(page_start: int | None, page_end: int | None) -> str:
    if page_start is None and page_end is None:
        return "unknown"
    if page_end is None or page_end == page_start:
        return str(page_start)
    if page_start is None:
        return str(page_end)
    return f"{page_start}-{page_end}"


def _preview(text: str, *, limit: int = 180) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


__all__ = ["rag_app"]
