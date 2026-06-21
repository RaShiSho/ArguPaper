"""Shared CLI command helpers."""

from pathlib import Path

from rich.console import Console

from argupaper.config import Config, load_config
from argupaper.memory.paper_store import PaperStore
from argupaper.workflows import AnalyzeWorkflow
from argupaper.workflows.convert import ConvertWorkflow
from argupaper.workflows.papers import PapersWorkflow
from argupaper.workflows.search import InteractiveSearchWorkflow

console = Console()
SPINNER_NAME = "line"
DEFAULT_OUTPUT_DIR = Path("output")


def build_analyze_workflow() -> AnalyzeWorkflow:
    """Construct the default analyze workflow."""

    config = load_config(require_pdf_api_key=False)
    return AnalyzeWorkflow(config)


def build_search_workflow() -> InteractiveSearchWorkflow:
    """Construct the default natural-language search workflow."""

    config = load_config(require_pdf_api_key=False)
    return InteractiveSearchWorkflow(config)


def build_convert_workflow() -> ConvertWorkflow:
    """Construct the default convert workflow."""

    config = load_config(require_pdf_api_key=True)
    return ConvertWorkflow(config)


def build_paper_store() -> PaperStore:
    """Construct the default local paper store."""

    config = load_config(require_pdf_api_key=False)
    return PaperStore(storage_path=config.paper_storage_path)


def build_papers_workflow() -> PapersWorkflow:
    """Construct the default saved-paper workflow."""

    return PapersWorkflow(build_paper_store())


def build_convert_pipeline(config: Config):
    """Backward-compatible placeholder for old CLI helper imports."""

    return ConvertWorkflow(config)._build_pipeline()


def resolve_analyze_output_path(output: str | None) -> Path | None:
    """Resolve analyze output paths."""

    if output is None:
        return None

    output_path = Path(output)
    has_explicit_path = any(separator in output for separator in ("/", "\\"))
    if output_path.is_absolute() or has_explicit_path:
        return output_path
    return DEFAULT_OUTPUT_DIR / output_path


def resolve_convert_output_path(output: str | None) -> Path | None:
    """Resolve convert export output paths exactly as provided."""

    if output is None:
        return None
    return Path(output)


def resolve_auto_report_path(paper_path: Path) -> Path:
    """Build the default report path from the input paper filename."""

    return DEFAULT_OUTPUT_DIR / f"{paper_path.stem}.md"


__all__ = [
    "SPINNER_NAME",
    "build_analyze_workflow",
    "build_convert_pipeline",
    "build_convert_workflow",
    "build_paper_store",
    "build_papers_workflow",
    "build_search_workflow",
    "console",
    "resolve_analyze_output_path",
    "resolve_auto_report_path",
    "resolve_convert_output_path",
]

