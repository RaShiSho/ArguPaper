"""JSONL logging for SciFact court evaluation runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ScifactEvalLogger:
    """Append-only JSONL logger for one SciFact evaluation run."""

    def __init__(self, base_dir: str | Path, run_id: str | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or uuid4().hex[:12]
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = self.base_dir / f"{stamp}-scifact-eval-{self.run_id}.jsonl"

    def write(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """Write one normalized event."""

        line = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "event": event,
            "payload": self._normalize(payload or {}),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    def _normalize(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): self._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        if isinstance(value, tuple):
            return [self._normalize(item) for item in value]
        return value


def preview_text(value: str | None, *, limit: int = 4000) -> str | None:
    """Return a bounded text preview for diagnostics."""

    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...[truncated {len(value) - limit} chars]"
