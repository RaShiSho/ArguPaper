"""JSONL audit logging for chat agent sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ChatRuntimeLogger:
    """Append-only JSONL logger for one chat session."""

    def __init__(self, base_dir: str | Path, session_id: str | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or uuid4().hex[:12]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = self.base_dir / f"{stamp}_{self.session_id}.jsonl"

    def write(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """Write one normalized event line."""

        line = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session_id": self.session_id,
            "event": event,
            "payload": self._normalize(payload or {}),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    def _normalize(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return {str(key): self._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        if isinstance(value, tuple):
            return [self._normalize(item) for item in value]
        return value
