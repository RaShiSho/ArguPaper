"""CLI commands for ArguPaper."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TaskProgressColumn
from rich.panel import Panel
from rich.markdown import Markdown

from argupaper.cli.formatters import format_search_results, format_error
from argupaper.config import load_config
from argupaper.pdf import PDFPipeline, MinerUClient, MarkdownCache
from argupaper.pdf.exceptions import RateLimitError, PDFPipelineError

console = Console()


def analyze(
    paper: str = typer.Argument(..., help="Path to PDF file or URL"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of debate rounds"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reconvert even if cached"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Analyze a research paper with multi-agent debate.

    Examples:

        argupaper analyze ./paper.pdf --output report.md

        argupaper analyze "https://arxiv.org/pdf/2301.12345.pdf" --output report.md --rounds 5
    """
    try:
        # Check if input is URL or file path
        if paper.startswith(("http://", "https://")):
            raise NotImplementedError(
                "URL analysis not yet implemented. "
                "Please download the PDF first and use local file path."
            )
        else:
            _run_analyze(paper, output, rounds, force, verbose)
    except Exception as e:
        console.print(format_error(e))
        raise typer.Exit(code=1)


def _run_analyze(
    paper_path: str,
    output: Optional[str],
    rounds: int,
    force: bool,
    verbose: bool,
) -> None:
    """Run the analysis pipeline synchronously."""
    # Load configuration
    try:
        config = load_config()
    except ValueError as e:
        raise RuntimeError(f"Configuration error: {e}")

    # Initialize pipeline components
    mineru_client = MinerUClient(
        api_key=config.pdf.api_key,
        model_version="vlm",
    )
    cache = MarkdownCache(cache_dir=config.pdf.cache_dir)
    pipeline = PDFPipeline(
        mineru_client=mineru_client,
        cache=cache,
        public_url_base=config.pdf.public_url_base,
    )

    # Run async pipeline
    try:
        markdown, cache_hit = asyncio.run(
            _process_pdf(pipeline, paper_path, force, verbose)
        )
    finally:
        asyncio.run(pipeline.close())

    # Show result
    if cache_hit:
        console.print("[dim]Result loaded from cache (use --force to reconvert)[/dim]\n")

    _display_report(markdown, output)


async def _process_pdf(
    pipeline: PDFPipeline,
    pdf_path: str,
    force: bool,
    verbose: bool,
) -> tuple[str, bool]:
    """Process PDF and return markdown content.

    Returns:
        tuple of (markdown_content, from_cache)
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing PDF...", total=None)

        try:
            # Step 1: PDF to Markdown conversion
            progress.update(task, description="[cyan]Converting PDF to Markdown...")
            result = await pipeline.process(pdf_path, force_reconvert=force)

            if result.status.value == "failed":
                raise RuntimeError(f"Conversion failed: {result.error}")

            cache_hit = result.from_cache
            markdown = result.markdown or ""

            if verbose and cache_hit:
                console.print(f"[dim]Cache key: {result.cache_key}[/dim]")

            # Step 2-5: Structure extraction, analysis, debate, report
            # TODO: Integrate with StructuredExtractor, AnalysisChain, DebateChain
            progress.update(task, description="[green]Extracting structure...")
            # placeholder for now - will add when extraction module is ready

            progress.update(task, description="[green]Running analysis...")
            # placeholder

            progress.update(task, description="[green]Running debate...")
            # placeholder

            progress.update(task, description="[green]Generating report...")
            report = _build_report(markdown, pdf_path, cache_hit)

            progress.update(task, completed=True)
            return report, cache_hit

        except RateLimitError as e:
            progress.stop()
            raise RuntimeError(
                f"API rate limit exceeded. Retry after {e.retry_after} seconds. "
                "Consider using --force to use cached results."
            )
        except PDFPipelineError as e:
            progress.stop()
            raise RuntimeError(f"PDF processing error: {e.message}")


def _build_report(markdown: str, pdf_path: str, from_cache: bool) -> str:
    """Build the final analysis report.

    TODO: Replace with actual chain integration when modules are ready.
    For now, returns a placeholder report with the markdown content.
    """
    # Extract title from markdown if available
    title = "Research Paper Analysis"
    if markdown:
        lines = markdown.split("\n")
        for line in lines[:10]:
            if line.startswith("# "):
                title = line[2:].strip()
                break

    cache_status = " (from cache)" if from_cache else ""

    report = f"""# {title}

## Document Info
- **Source**: {Path(pdf_path).name}
- **Status**: PDF conversion successful{cache_status}

## Paper Content

{markdown[:2000]}{"..." if len(markdown) > 2000 else ""}

---

## Analysis Pipeline Status
- [x] PDF Processing: Complete
- [ ] Structure Extraction: Pending (not yet integrated)
- [ ] Analysis: Pending (not yet integrated)
- [ ] Debate: Pending (not yet integrated)
- [ ] Report Generation: Placeholder

## Next Steps
Implement the analysis chains to see full research critique.

## Raw Markdown Storage
Full markdown is cached and available for subsequent analysis runs.
"""
    return report


def _display_report(markdown: str, output: Optional[str]) -> None:
    """Display the analysis report."""
    console.print(Panel("[bold green]Analysis Complete[/bold green]", expand=False))

    if output:
        output_path = Path(output)
        output_path.write_text(markdown, encoding="utf-8")
        console.print(f"[dim]Report saved to: {output_path.absolute()}[/dim]")

    console.print(Markdown(markdown))


def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results"),
    source: str = typer.Option("both", "--source", "-s",
        help="Search source: semantic_scholar, arxiv, or both"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Search for academic papers.

    Examples:

        argupaper search "machine learning theory" --limit 10

        argupaper search "transformer attention" --source semantic_scholar --limit 5
    """
    try:
        _run_search(query, limit, source, verbose)
    except Exception as e:
        console.print(format_error(e))
        raise typer.Exit(code=1)


def _run_search(query: str, limit: int, source: str, verbose: bool) -> None:
    """Run paper search.

    TODO: Integrate with actual retrieval module when ready.
    Currently shows placeholder results.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Searching: {query}...", total=None)

        # TODO: Integrate with SemanticScholarClient, ArXivClient
        # For now, simulate with placeholder
        results = [
            {
                "title": f"Simulated Paper {i+1} related to: {query}",
                "authors": ["Author A", "Author B"],
                "year": 2024,
                "venue": "NeurIPS",
                "citation_count": 42 + i,
                "url": f"https://arxiv.org/abs/2301.{i:05d}",
            }
            for i in range(min(limit, 5))
        ]

        progress.update(task, completed=True)

    console.print(Panel("[bold green]Search Results[/bold green]", expand=False))
    console.print("[dim]Note: Search is simulated. Integration pending.[/dim]\n")
    console.print(format_search_results(results))


def get_app() -> typer.Typer:
    """Get the Typer app instance for programmatic use."""
    from argupaper.cli import app
    return app
