## Context

The current `convert` command validates a single local PDF, creates `MarkdownCache`, `MinerUClient`, and `PDFPipeline`, then prints cache details. The PDF pipeline already handles cache lookup, force reconversion, MinerU upload/polling, and cache writes, so folder mode should orchestrate multiple inputs without changing conversion internals.

## Goals / Non-Goals

**Goals:**

- Support one-shot conversion of all direct PDF files in a user-provided folder.
- Preserve single-file `convert` behavior and the meaning of `--force/-f`.
- Make skipped files, failures, successes, cache hits, and processed paths visible in CLI output and durable logs.
- Keep the implementation small and sequential to avoid MinerU rate-limit surprises.

**Non-Goals:**

- No recursive directory traversal.
- No per-file Markdown export in folder mode.
- No Web UI/API change.
- No change to cache key generation or MinerU request behavior.

## Decisions

- **Use `--folder/-d` for folder input.** `-f` already means `--force`; preserving it avoids breaking existing scripts.
- **Keep `pdf` optional but mutually exclusive with `--folder`.** This provides clear validation for missing or duplicate input sources.
- **Sequential processing.** A single pipeline instance is reused for all eligible PDFs and closed at the end.
- **Best-effort batch semantics.** Skips and per-file conversion errors are recorded and the batch continues.
- **JSONL run logs.** Each run receives a timestamped run id under `data/convert_runs/<run-id>.jsonl`, with one event per line for machine-readable tracing.

## Risks / Trade-offs

- Directory mode can take a long time for many PDFs; sequential processing favors reliability over throughput.
- A folder containing no PDFs still succeeds with a summary showing only skipped entries, because skips are expected behavior.
- Logs may contain local absolute paths; this is acceptable for a local CLI tool and necessary for traceability.
