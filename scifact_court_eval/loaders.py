"""Load SciFact JSONL files for court evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scifact_court_eval.models import GoldEvidenceSet, ScifactClaim, ScifactDocument

DEFAULT_SCIFACT_DATA_DIR = Path("sample/scifact/data")


def load_corpus(data_dir: Path = DEFAULT_SCIFACT_DATA_DIR) -> dict[int, ScifactDocument]:
    """Load SciFact corpus documents keyed by doc_id."""

    corpus_path = data_dir / "corpus.jsonl"
    documents: dict[int, ScifactDocument] = {}
    for row in _read_jsonl(corpus_path):
        document = ScifactDocument.model_validate(row)
        documents[document.doc_id] = document
    return documents


def load_claims(split: str, data_dir: Path = DEFAULT_SCIFACT_DATA_DIR) -> list[ScifactClaim]:
    """Load SciFact claims for one split."""

    normalized = split.strip().lower()
    path = data_dir / f"claims_{normalized}.jsonl"
    claims: list[ScifactClaim] = []
    for row in _read_jsonl(path):
        claims.append(_claim_from_row(row, normalized))
    return claims


def gold_chunk_ids(claim: ScifactClaim) -> list[str]:
    """Return gold SciFact chunk ids for one claim."""

    ids: list[str] = []
    for evidence_set in claim.evidence_sets:
        for sentence_idx in evidence_set.sentences:
            ids.append(scifact_chunk_id(evidence_set.doc_id, sentence_idx))
    return list(dict.fromkeys(ids))


def scifact_chunk_id(doc_id: int, sentence_idx: int) -> str:
    """Build the stable chunk id used in Milvus."""

    return f"scifact:{doc_id}:sent:{sentence_idx}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"SciFact file not found: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _claim_from_row(row: dict[str, Any], split: str) -> ScifactClaim:
    evidence_sets: list[GoldEvidenceSet] = []
    evidence = row.get("evidence") or {}
    if isinstance(evidence, dict):
        for raw_doc_id, entries in evidence.items():
            for entry in entries or []:
                evidence_sets.append(
                    GoldEvidenceSet(
                        doc_id=int(raw_doc_id),
                        sentences=[int(item) for item in entry.get("sentences", [])],
                        label=str(entry.get("label", "NOT_ENOUGH_INFO")),
                    )
                )
    return ScifactClaim(
        claim_id=int(row["id"]),
        text=str(row["claim"]),
        split=split,
        cited_doc_ids=[int(item) for item in row.get("cited_doc_ids", [])],
        evidence_sets=evidence_sets,
    )

