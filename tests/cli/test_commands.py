"""CLI tests for ArguPaper commands."""

from pathlib import Path

from typer.testing import CliRunner

from argupaper.cli import app
from argupaper.workflows.models import (
    AnalyzeOptions,
    AnalyzeWorkflowResult,
    SearchOptions,
    SearchResult,
    SearchWorkflowResult,
)


runner = CliRunner()


class StubAnalyzeWorkflow:
    """Simple analyze workflow stub for CLI tests."""

    def run_sync(self, options: AnalyzeOptions, progress_callback=None) -> AnalyzeWorkflowResult:
        if progress_callback:
            progress_callback("Generating report...")
        return AnalyzeWorkflowResult(
            report_markdown="# Report\n\nBody",
            report_title="Stub Report",
            from_cache=True,
            paper_id="paper-123",
            supplementary_search_used=True,
            warnings=["supplementary retrieval failed"],
        )


class StubSearchWorkflow:
    """Simple search workflow stub for CLI tests."""

    def __init__(self, results=None, warnings=None):
        self._results = results if results is not None else [
            SearchResult(
                title="Attention Is All You Need",
                authors=["A", "B"],
                year=2017,
                venue="NeurIPS",
                citation_count=1000,
                url="https://arxiv.org/abs/1706.03762",
                source="arxiv",
            )
        ]
        self._warnings = warnings or []

    def run_sync(self, options: SearchOptions, progress_callback=None) -> SearchWorkflowResult:
        if progress_callback:
            progress_callback("Searching paper sources...")
        return SearchWorkflowResult(
            results=self._results,
            expanded_queries=[options.query, f"{options.query} expansion"],
            source_stats={"arxiv": len(self._results)},
            warnings=self._warnings,
        )


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.stdout
    assert "search" in result.stdout


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_analyze_happy_path(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    output_path = tmp_path / "report.md"

    monkeypatch.setattr("argupaper.cli.commands.build_analyze_workflow", lambda: StubAnalyzeWorkflow())

    result = runner.invoke(app, ["analyze", str(pdf_path), "--output", str(output_path)])

    assert result.exit_code == 0
    assert "Analysis complete" in result.stdout
    assert "Paper ID: paper-123" in result.stdout
    assert output_path.read_text(encoding="utf-8") == "# Report\n\nBody"


def test_analyze_rejects_url() -> None:
    result = runner.invoke(app, ["analyze", "https://example.com/paper.pdf"])
    assert result.exit_code == 1
    assert "URL analysis is not part of the MVP CLI" in result.stdout


def test_search_happy_path(monkeypatch) -> None:
    monkeypatch.setattr("argupaper.cli.commands.build_search_workflow", lambda: StubSearchWorkflow())

    result = runner.invoke(app, ["search", "transformer"])

    assert result.exit_code == 0
    assert "Search complete" in result.stdout
    assert "Attention Is All You Need" in result.stdout
    assert "simulated" not in result.stdout.lower()


def test_search_invalid_source() -> None:
    result = runner.invoke(app, ["search", "transformer", "--source", "invalid"])
    assert result.exit_code == 1
    assert "--source must be one of" in result.stdout


def test_search_empty_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "argupaper.cli.commands.build_search_workflow",
        lambda: StubSearchWorkflow(results=[]),
    )

    result = runner.invoke(app, ["search", "transformer"])

    assert result.exit_code == 0
    assert "No results found" in result.stdout


def test_search_all_sources_failed(monkeypatch) -> None:
    monkeypatch.setattr(
        "argupaper.cli.commands.build_search_workflow",
        lambda: StubSearchWorkflow(results=[], warnings=["semantic_scholar search failed"]),
    )

    result = runner.invoke(app, ["search", "transformer"])

    assert result.exit_code == 1
    assert "All search sources failed" in result.stdout
