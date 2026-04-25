"""Paper storage with structured knowledge layers."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class PaperStore:
    """Storage for papers with Level 1-3 structured knowledge."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path("./data/papers")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save_paper(self, paper_id: str, knowledge: dict) -> None:
        """Save paper with structured knowledge."""

        paper_dir = self.storage_path / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)

        metadata = knowledge.get("metadata", {})
        abstract = knowledge.get("abstract", {})
        markdown = knowledge.get("markdown", "")
        report = knowledge.get("report", "")

        (paper_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (paper_dir / "abstract.json").write_text(
            json.dumps(abstract, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (paper_dir / "paper.md").write_text(markdown, encoding="utf-8")
        (paper_dir / "report.md").write_text(report, encoding="utf-8")

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """Retrieve paper by ID."""

        paper_dir = self._resolve_paper_dir(paper_id)
        if paper_dir is None:
            return None

        return self._read_paper_dir(paper_dir)

    async def list_papers(self) -> list[dict]:
        """List saved paper metadata sorted by most recent update."""

        records: list[dict] = []
        for paper_dir in self.storage_path.iterdir():
            if not paper_dir.is_dir():
                continue
            metadata = self._read_metadata(paper_dir)
            if not metadata:
                continue
            records.append(metadata)
        return sorted(records, key=lambda item: str(item.get("updated_at", "")), reverse=True)

    async def search_papers(self, query: str) -> list[dict]:
        """Semantic search across papers."""

        lowered = query.lower()
        matches: list[dict] = []
        for paper_dir in self.storage_path.iterdir():
            if not paper_dir.is_dir():
                continue
            metadata = self._read_metadata(paper_dir)
            if not metadata:
                continue
            abstract_path = paper_dir / "abstract.json"
            abstract_text = ""
            if abstract_path.exists():
                abstract_text = abstract_path.read_text(encoding="utf-8")
            searchable_text = " ".join(
                [
                    *(str(metadata.get(field, "")) for field in ("title", "source", "paper_id")),
                    abstract_text,
                ]
            ).lower()
            if lowered in searchable_text:
                matches.append(metadata)
        return sorted(matches, key=lambda item: str(item.get("updated_at", "")), reverse=True)

    def _resolve_paper_dir(self, paper_id: str) -> Optional[Path]:
        normalized = str(paper_id or "").strip()
        if not normalized:
            return None
        if any(separator in normalized for separator in ("/", "\\")):
            return None

        exact = self.storage_path / normalized
        if exact.is_dir():
            return exact

        matches = [
            paper_dir
            for paper_dir in self.storage_path.iterdir()
            if paper_dir.is_dir() and paper_dir.name.startswith(normalized)
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def _read_paper_dir(self, paper_dir: Path) -> dict:
        result: dict = {}
        metadata = self._read_metadata(paper_dir)
        if metadata:
            result["metadata"] = metadata

        abstract_path = paper_dir / "abstract.json"
        paper_path = paper_dir / "paper.md"
        report_path = paper_dir / "report.md"

        if abstract_path.exists():
            result["abstract"] = json.loads(abstract_path.read_text(encoding="utf-8"))
        if paper_path.exists():
            result["markdown"] = paper_path.read_text(encoding="utf-8")
        if report_path.exists():
            result["report"] = report_path.read_text(encoding="utf-8")
        return result

    def _read_metadata(self, paper_dir: Path) -> dict:
        metadata_path = paper_dir / "metadata.json"
        if not metadata_path.exists():
            return {}
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.setdefault("paper_id", paper_dir.name)
        metadata["updated_at"] = self._format_mtime(metadata_path)
        return metadata

    def _format_mtime(self, path: Path) -> str:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return modified_at.isoformat(timespec="seconds")
