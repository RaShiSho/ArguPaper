"""Paper storage with structured knowledge layers."""

import json
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

        paper_dir = self.storage_path / paper_id
        if not paper_dir.exists():
            return None

        result: dict = {}
        metadata_path = paper_dir / "metadata.json"
        abstract_path = paper_dir / "abstract.json"
        paper_path = paper_dir / "paper.md"
        report_path = paper_dir / "report.md"

        if metadata_path.exists():
            result["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
        if abstract_path.exists():
            result["abstract"] = json.loads(abstract_path.read_text(encoding="utf-8"))
        if paper_path.exists():
            result["markdown"] = paper_path.read_text(encoding="utf-8")
        if report_path.exists():
            result["report"] = report_path.read_text(encoding="utf-8")
        return result

    async def search_papers(self, query: str) -> list[dict]:
        """Semantic search across papers."""

        lowered = query.lower()
        matches: list[dict] = []
        for paper_dir in self.storage_path.iterdir():
            if not paper_dir.is_dir():
                continue
            metadata_path = paper_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            searchable_text = " ".join(
                str(metadata.get(field, "")) for field in ("title", "source", "paper_id")
            ).lower()
            if lowered in searchable_text:
                matches.append(metadata)
        return matches
