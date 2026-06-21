"""CLI command entrypoints."""

from argupaper.cli.commands.chat import chat
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
from argupaper.cli.commands.court import court
from argupaper.cli.commands.debate import debate
from argupaper.cli.commands.papers import papers
from argupaper.cli.commands.rag import rag_app
from argupaper.cli.commands.search import search

__all__ = [
    "build_analyze_workflow",
    "build_convert_pipeline",
    "build_paper_store",
    "build_search_workflow",
    "chat",
    "convert",
    "court",
    "debate",
    "papers",
    "rag_app",
    "resolve_analyze_output_path",
    "resolve_auto_report_path",
    "resolve_convert_output_path",
    "search",
]
