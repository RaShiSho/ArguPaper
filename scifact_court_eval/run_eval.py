"""Command line runner for SciFact court evaluation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from argupaper.config import Config, load_config

from scifact_court_eval.baseline import DirectReadBaseline
from scifact_court_eval.court_runner import ScifactCourtRunner
from scifact_court_eval.indexer import SCIFACT_COLLECTION, ScifactIndexer
from scifact_court_eval.judge import ScifactJudge
from scifact_court_eval.loaders import DEFAULT_SCIFACT_DATA_DIR, load_claims, load_corpus
from scifact_court_eval.eval_logging import ScifactEvalLogger
from scifact_court_eval.metrics import build_record, summarize
from scifact_court_eval.models import EvaluationRecord, JudgeScore, ScifactClaim
from scifact_court_eval.reporting import write_reports

DEFAULT_OUTPUT_DIR = Path("output/scifact_court_eval")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        asyncio.run(run_eval(args))
        return 0
    if args.command == "cleanup-index":
        cleanup_index(args)
        return 0
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate ArguPaper PaperCourtGraph on SciFact with an isolated Milvus collection."
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="run end-to-end SciFact court evaluation")
    run_parser.add_argument("--split", default="dev", choices=("dev", "test"), help="SciFact split")
    run_parser.add_argument("--limit", type=int, default=50, help="maximum claims to evaluate")
    run_parser.add_argument("--top-k", type=int, default=10, help="RAG retrieval top-k")
    run_parser.add_argument("--max-rounds", type=int, default=1, help="court debate max rounds")
    run_parser.add_argument(
        "--index-if-missing",
        action="store_true",
        help="build SciFact eval index only when the isolated collection is missing",
    )
    run_parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="drop the isolated collection and rebuild the index",
    )
    run_parser.add_argument(
        "--index-scope",
        default="all",
        choices=("all", "claims"),
        help="index all SciFact corpus docs or only docs cited by the evaluated claims",
    )
    run_parser.add_argument(
        "--collection",
        default=SCIFACT_COLLECTION,
        help="isolated Milvus collection for SciFact eval chunks",
    )
    run_parser.add_argument("--batch-size", type=int, default=8, help="embedding batch size")
    run_parser.add_argument("--judge-provider", default="default", help="LLM provider alias for judge")
    run_parser.add_argument("--baseline-provider", default="default", help="LLM provider alias for baseline")
    run_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_SCIFACT_DATA_DIR,
        help="SciFact data directory containing corpus.jsonl and claims_*.jsonl",
    )
    run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="directory for results.jsonl, summary.md, failures.md, and judge_traces.jsonl",
    )
    run_parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="directory for SciFact evaluation JSONL run logs",
    )

    cleanup_parser = subparsers.add_parser(
        "cleanup-index",
        help="delete SciFact eval chunks from the isolated Milvus collection",
    )
    cleanup_parser.add_argument(
        "--collection",
        default=SCIFACT_COLLECTION,
        help="isolated Milvus collection to clean",
    )
    return parser


async def run_eval(args: argparse.Namespace) -> None:
    config = load_config(require_pdf_api_key=False)
    log_dir = args.log_dir or (Path(config.log.root_path) / "scifact")
    logger = ScifactEvalLogger(log_dir)
    print(f"SciFact eval log: {logger.path.resolve()}")
    corpus = load_corpus(args.data_dir)
    claims = load_claims(args.split, args.data_dir)
    if args.limit is not None and args.limit > 0:
        claims = claims[: args.limit]

    logger.write(
        "run_start",
        {
            "split": args.split,
            "limit": args.limit,
            "top_k": args.top_k,
            "max_rounds": args.max_rounds,
            "collection": args.collection,
            "index_scope": args.index_scope,
            "batch_size": args.batch_size,
            "index_if_missing": args.index_if_missing,
            "rebuild_index": args.rebuild_index,
            "judge_provider": args.judge_provider,
            "baseline_provider": args.baseline_provider,
            "data_dir": args.data_dir,
            "output_dir": args.output_dir,
        },
    )
    print(f"Loaded {len(corpus)} SciFact documents and {len(claims)} {args.split} claims.")
    index_corpus = select_index_corpus(corpus, claims, scope=args.index_scope)
    print(
        f"Index scope '{args.index_scope}' contains {len(index_corpus)} documents "
        f"out of {len(corpus)}."
    )
    await ensure_index(config, index_corpus, args, logger=logger)

    court = ScifactCourtRunner(
        config,
        top_k=args.top_k,
        max_rounds=args.max_rounds,
        collection=args.collection,
    )
    baseline = DirectReadBaseline(config, provider_alias=args.baseline_provider, logger=logger)
    judge = ScifactJudge(config, provider_alias=args.judge_provider, logger=logger)
    records: list[EvaluationRecord] = []
    try:
        for index, claim in enumerate(claims, start=1):
            print(f"[{index}/{len(claims)}] Evaluating claim {claim.claim_id}...")
            logger.write(
                "claim_start",
                {
                    "claim_index": index,
                    "claim_total": len(claims),
                    "claim_id": claim.claim_id,
                    "gold_label": claim.gold_label,
                    "cited_doc_ids": claim.cited_doc_ids,
                },
            )
            record = await evaluate_claim(
                claim,
                corpus=corpus,
                court=court,
                baseline=baseline,
                judge=judge,
                logger=logger,
            )
            records.append(record)
            persist_partial(args.output_dir, records)
    finally:
        await baseline.close()
        await judge.close()

    summary = summarize(records)
    write_outputs(args.output_dir, records, summary)
    logger.write(
        "run_summary",
        {
            "summary": summary,
            "results_path": args.output_dir / "results.jsonl",
            "judge_traces_path": args.output_dir / "judge_traces.jsonl",
            "summary_json_path": args.output_dir / "summary.json",
            "summary_md_path": args.output_dir / "summary.md",
            "failures_path": args.output_dir / "failures.md",
        },
    )
    print(f"Wrote results to {args.output_dir.resolve()}")
    print(f"Total trust score: {summary.total_trust_score:.4f}")


async def ensure_index(
    config: Config,
    corpus: dict[int, Any],
    args: argparse.Namespace,
    *,
    logger: ScifactEvalLogger,
) -> None:
    if not args.index_if_missing and not args.rebuild_index:
        print(f"Using existing SciFact eval collection: {args.collection}")
        logger.write(
            "index_summary",
            {
                "status": "skipped",
                "reason": "index_if_missing and rebuild_index are both false",
                "collection": args.collection,
                "document_count": len(corpus),
            },
        )
        return

    indexer = ScifactIndexer(config, collection=args.collection)
    try:
        chunk_count = len(indexer.iter_chunk_records(corpus, split=args.split))
        logger.write(
            "index_start",
            {
                "collection": args.collection,
                "document_count": len(corpus),
                "chunk_count": chunk_count,
                "batch_size": args.batch_size,
                "rebuild_index": args.rebuild_index,
                "index_if_missing": args.index_if_missing,
            },
        )
        exists = indexer.collection_exists()
        should_index = args.rebuild_index or not exists
        if not should_index:
            print(f"SciFact eval collection already exists: {args.collection}")
            logger.write(
                "index_summary",
                {
                    "status": "skipped",
                    "reason": "collection already exists",
                    "collection": args.collection,
                    "document_count": len(corpus),
                    "chunk_count": chunk_count,
                },
            )
            return
        indexed = await indexer.index_corpus(
            corpus,
            split=args.split,
            batch_size=args.batch_size,
            rebuild=args.rebuild_index,
            progress_callback=print,
            event_callback=logger.write,
        )
        logger.write(
            "index_summary",
            {
                "status": "completed",
                "collection": args.collection,
                "document_count": len(corpus),
                "chunk_count": chunk_count,
                "indexed_count": indexed,
            },
        )
        print(f"Indexed {indexed} SciFact chunks into {args.collection}.")
    except Exception as exc:
        logger.write(
            "index_failed",
            {
                "collection": args.collection,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise
    finally:
        await indexer.close()


async def evaluate_claim(
    claim: ScifactClaim,
    *,
    corpus: dict[int, Any],
    court: ScifactCourtRunner,
    baseline: DirectReadBaseline,
    judge: ScifactJudge,
    logger: ScifactEvalLogger,
) -> EvaluationRecord:
    baseline_result = await _run_baseline(baseline, claim, corpus)
    court_report = await _run_court(court, claim)
    logger.write(
        "court_result",
        {
            "claim_id": claim.claim_id,
            "court_failed": court_report.get("failed"),
            "error": court_report.get("error"),
            "predicted_verdict": _first_verdict(court_report),
            "evidence_chunk_ids": _evidence_chunk_ids(court_report),
            "warnings": court_report.get("warnings", []),
        },
    )
    judge_score = await judge.score(
        claim=claim,
        corpus=corpus,
        court_report=court_report,
        baseline=baseline_result,
    )
    record = build_record(
        claim=claim,
        court_report=court_report,
        judge=judge_score,
        baseline=baseline_result,
    )
    logger.write(
        "claim_summary",
        {
            "claim_id": record.claim_id,
            "gold_label": record.gold_label,
            "predicted_verdict": record.predicted_verdict,
            "predicted_label": record.predicted_label,
            "verdict_correct": record.verdict_correct,
            "doc_hit": record.doc_hit,
            "sentence_hit": record.sentence_hit,
            "supported_hallucination": record.supported_hallucination,
            "judge_failed": record.judge.failed,
        },
    )
    return record


async def _run_baseline(
    baseline: DirectReadBaseline,
    claim: ScifactClaim,
    corpus: dict[int, Any],
) -> dict[str, Any]:
    try:
        return await baseline.run(claim, corpus=corpus)
    except Exception as exc:  # noqa: BLE001 - keep batch evaluation moving
        return {"failed": True, "error": str(exc)}


async def _run_court(court: ScifactCourtRunner, claim: ScifactClaim) -> dict[str, Any]:
    try:
        return await court.run_claim(claim)
    except Exception as exc:  # noqa: BLE001 - keep batch evaluation moving
        return {
            "claim": claim.text,
            "evidence": [],
            "challenge": [],
            "defense": [],
            "unresolved_disputes": [],
            "verdicts": [
                {
                    "claim_id": f"scifact-claim-{claim.claim_id}",
                    "verdict": "needs_external_validation",
                    "confidence": 0.0,
                    "rationale": f"court_failed: {exc}",
                    "required_check": ["inspect court runtime failure"],
                }
            ],
            "required_check": ["court_failed"],
            "failed": True,
            "error": str(exc),
        }


def persist_partial(output_dir: Path, records: list[EvaluationRecord]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "results.jsonl", [record.model_dump(mode="json") for record in records])
    write_jsonl(
        output_dir / "judge_traces.jsonl",
        [
            {
                "claim_id": record.claim_id,
                "judge": record.judge.model_dump(mode="json"),
                "judge_failed": record.judge.failed,
            }
            for record in records
        ],
    )


def write_outputs(
    output_dir: Path,
    records: list[EvaluationRecord],
    summary: Any,
) -> None:
    persist_partial(output_dir, records)
    (output_dir / "summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_reports(output_dir, records=records, summary=summary)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def _first_verdict(court_report: dict[str, Any]) -> str:
    verdicts = court_report.get("verdicts") or []
    if verdicts and isinstance(verdicts[0], dict):
        return str(verdicts[0].get("verdict") or "needs_external_validation")
    return "needs_external_validation"


def _evidence_chunk_ids(court_report: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in court_report.get("evidence", []) or []:
        if isinstance(item, dict):
            chunk_id = str(item.get("chunk_id", "")).strip()
            if chunk_id:
                ids.append(chunk_id)
    return list(dict.fromkeys(ids))


def select_index_corpus(
    corpus: dict[int, Any],
    claims: list[ScifactClaim],
    *,
    scope: str,
) -> dict[int, Any]:
    if scope == "all":
        return corpus
    doc_ids: set[int] = set()
    for claim in claims:
        doc_ids.update(claim.cited_doc_ids)
        doc_ids.update(evidence.doc_id for evidence in claim.evidence_sets)
    return {doc_id: corpus[doc_id] for doc_id in sorted(doc_ids) if doc_id in corpus}


def cleanup_index(args: argparse.Namespace) -> None:
    config = load_config(require_pdf_api_key=False)
    indexer = ScifactIndexer(config, collection=args.collection)
    try:
        dropped = indexer.drop_collection()
    finally:
        asyncio.run(indexer.close())
    print(
        f"Dropped SciFact eval collection={args.collection}: {dropped}. "
        "Default paper_chunks was not touched."
    )


if __name__ == "__main__":
    raise SystemExit(main())
