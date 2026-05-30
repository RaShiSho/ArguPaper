"""File logging setup for the local web workbench."""

from __future__ import annotations

import logging
from pathlib import Path


WEB_BACKEND_LOG_NAME = "web-backend.log"


def configure_web_logging(log_path: str | Path) -> Path:
    """Configure backend loggers to write under the web log directory."""

    log_dir = Path(log_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / WEB_BACKEND_LOG_NAME

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for logger_name in ("argupaper.web", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        if _has_file_handler(logger, log_file):
            continue
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return log_file


def _has_file_handler(logger: logging.Logger, log_file: Path) -> bool:
    resolved_log_file = log_file.resolve()
    for handler in logger.handlers:
        if not isinstance(handler, logging.FileHandler):
            continue
        try:
            if Path(handler.baseFilename).resolve() == resolved_log_file:
                return True
        except OSError:
            continue
    return False
