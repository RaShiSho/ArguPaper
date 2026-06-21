"""Compatibility layer for chat tools.

Tool implementations live in :mod:`argupaper.tools`. This module remains only
for older imports that still expect ``argupaper.agents.chat.tools``.
"""

from __future__ import annotations

from typing import Any

from argupaper.config import Config
from argupaper.tools import (
    DebatePaperArgs,
    LangChainToolbox,
    ListPapersArgs,
    ReadPaperContextArgs,
    ReadPaperFullTextArgs,
    SearchPapersArgs,
    SelectPaperArgs,
    build_default_toolbox,
)
from argupaper.tools.factory import ProgressCallback


class ChatToolbox:
    """Backward-compatible wrapper around the default unified toolbox."""

    def __new__(
        cls,
        config: Config,
        progress_callback: ProgressCallback = None,
    ) -> LangChainToolbox:
        return build_default_toolbox(config, progress_callback=progress_callback)


def default_paper_id(arguments: dict[str, Any], selected_paper: dict[str, Any] | None) -> dict[str, Any]:
    """Fill paper_id from the selected paper when a tool omitted it."""

    if arguments.get("paper_id") or selected_paper is None:
        return arguments
    filled = dict(arguments)
    filled["paper_id"] = selected_paper.get("paper_id")
    return filled


__all__ = [
    "ChatToolbox",
    "DebatePaperArgs",
    "ListPapersArgs",
    "ReadPaperContextArgs",
    "ReadPaperFullTextArgs",
    "SearchPapersArgs",
    "SelectPaperArgs",
    "default_paper_id",
]
