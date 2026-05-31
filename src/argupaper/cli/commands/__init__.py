"""CLI command entrypoints."""

from argupaper.cli.commands.analyze import analyze
from argupaper.cli.commands.common import (
    build_analyze_workflow,
    build_convert_pipeline,
    build_paper_store,
    build_search_workflow,
    resolve_analyze_output_path,
    resolve_auto_report_path,
    resolve_convert_output_path,
)
from argupaper.cli.commands.convert import convert
from argupaper.cli.commands.papers import papers
from argupaper.cli.commands.search import search

__all__ = [
    "analyze",
    "build_analyze_workflow",
    "build_convert_pipeline",
    "build_paper_store",
    "build_search_workflow",
    "convert",
    "papers",
    "resolve_analyze_output_path",
    "resolve_auto_report_path",
    "resolve_convert_output_path",
    "search",
]
"""CLI command exports."""

from argupaper.cli.commands.analyze import analyze
from argupaper.cli.commands.chat import chat
from argupaper.cli.commands.convert import convert
from argupaper.cli.commands.papers import papers
from argupaper.cli.commands.search import search

__all__ = ["analyze", "chat", "convert", "papers", "search"]
