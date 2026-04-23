"""Pytest configuration shared across the test suite."""

from __future__ import annotations

import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PYTEST_ROOT = ROOT / ".pytest"
PYTEST_CACHE_DIR = PYTEST_ROOT / "cache"
PYTEST_TMP_DIR = PYTEST_ROOT / "tmp"
PYTEST_WORKSPACE_DIR = PYTEST_ROOT / "workspace"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session", autouse=True)
def ensure_pytest_directories() -> None:
    """Ensure the repository-local pytest directories exist before tests run."""

    for path in (PYTEST_CACHE_DIR, PYTEST_TMP_DIR, PYTEST_WORKSPACE_DIR):
        path.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def workspace_dir() -> Iterator[Path]:
    """Create a manual test workspace under .pytest/workspace."""

    PYTEST_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="analyze_", dir=PYTEST_WORKSPACE_DIR))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
