"""CLI tests for ArguPaper commands."""

from pathlib import Path
from typer.testing import CliRunner

from argupaper.cli import app
from argupaper.cli.commands import _run_search
from argupaper.workflows.models import (
    AnalyzeOptions,
    AnalyzeWorkflowResult,
    SearchAgentResult,
    SearchClarification,
    SearchClarificationOption,
    SearchFilters,
    SearchOptions,
    SearchParseResult,
    SearchResult,
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


class StubSearchAgentWorkflow:
    """Simple search-agent workflow stub for CLI tests."""

    def __init__(self, results=None, warnings=None, retrieved_count=None):
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
        self._retrieved_count = retrieved_count if retrieved_count is not None else len(self._results)

    def run_sync(
        self,
        options: SearchOptions,
        progress_callback=None,
        clarification_callback=None,
    ) -> SearchAgentResult:
        if progress_callback:
            progress_callback("Retrieving candidate papers...")
        return SearchAgentResult(
            results=self._results,
            expanded_queries=[options.query, f"{options.query} expansion"],
            source_stats={"arxiv": len(self._results)},
            warnings=self._warnings,
            trace_dir=str(Path.cwd() / ".pytest" / "workspace" / "agent_runs" / "search" / "stub"),
            parse_result=SearchParseResult(
                raw_request=options.raw_request or options.query,
                filters=SearchFilters(keywords=[options.query], target_count=options.limit),
                parser="heuristic",
            ),
            retrieved_count=self._retrieved_count,
            filtered_count=len(self._results),
            candidate_limit=max(options.limit, len(self._results)),
        )


class ClarifyingSearchAgentWorkflow(StubSearchAgentWorkflow):
    """Stub workflow that requires one clarification."""

    def __init__(self):
        super().__init__()
        self.selected_value: str | None = None

    def run_sync(
        self,
        options: SearchOptions,
        progress_callback=None,
        clarification_callback=None,
    ) -> SearchAgentResult:
        assert clarification_callback is not None
        response = clarification_callback(
            SearchClarification(
                field="venue_policy",
                prompt="How should the venue requirement be interpreted?",
                options=[
                    SearchClarificationOption(value="strict_journal", label="Journal only"),
                    SearchClarificationOption(value="none", label="No venue filter"),
                ],
            )
        )
        self.selected_value = response.selected_value
        return super().run_sync(options, progress_callback, clarification_callback)


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
    monkeypatch.setattr(
        "argupaper.cli.commands.build_search_agent_workflow",
        lambda: StubSearchAgentWorkflow(),
    )

    result = runner.invoke(app, ["search", "transformer"])

    assert result.exit_code == 0
    assert "Search complete" in result.stdout
    assert "Attention Is All You Need" in result.stdout
    assert "Trace saved to:" in result.stdout
    assert "simulated" not in result.stdout.lower()


def test_search_invalid_source() -> None:
    result = runner.invoke(app, ["search", "transformer", "--source", "invalid"])
    assert result.exit_code == 1
    assert "--source must be one of" in result.stdout


def test_search_empty_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "argupaper.cli.commands.build_search_agent_workflow",
        lambda: StubSearchAgentWorkflow(results=[]),
    )

    result = runner.invoke(app, ["search", "transformer"])

    assert result.exit_code == 0
    assert "No results found" in result.stdout


def test_search_all_sources_failed(monkeypatch) -> None:
    monkeypatch.setattr(
        "argupaper.cli.commands.build_search_agent_workflow",
        lambda: StubSearchAgentWorkflow(
            results=[],
            warnings=["semantic_scholar search failed"],
            retrieved_count=0,
        ),
    )

    result = runner.invoke(app, ["search", "transformer"])

    assert result.exit_code == 1
    assert "All search sources failed" in result.stdout


def test_search_interactive_clarification(monkeypatch) -> None:
    workflow = ClarifyingSearchAgentWorkflow()
    monkeypatch.setattr("argupaper.cli.commands.typer.prompt", lambda *args, **kwargs: 1)

    _run_search(
        workflow,
        SearchOptions(
            query="agent attack 权威期刊",
            raw_request="agent attack 权威期刊",
            interactive=True,
        ),
    )

    assert workflow.selected_value == "strict_journal"
