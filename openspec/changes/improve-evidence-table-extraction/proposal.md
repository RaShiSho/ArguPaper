## Why

Current `analyze` reports often render an almost empty Evidence Table because experiment extraction only matches a very small hard-coded dataset and metric list. This blocks the MVP promise of evidence-aware paper analysis more directly than larger future work such as 4-Agent debate or knowledge graph reasoning.

## What Changes

- Improve experiment extraction from Markdown sections such as Experiments, Evaluation, Results, Datasets, Metrics, and Benchmarks.
- Recognize dataset and metric names beyond the current tiny allowlist by combining expanded known terms with pattern-based extraction.
- Generate more informative Evidence Table rows with dataset, metric, and support snippets instead of only generic placeholders.
- Keep the implementation deterministic and local; no new external API or LLM dependency is introduced.
- Add smoke coverage for representative Markdown where datasets and metrics are not in the previous allowlist.

## Capabilities

### New Capabilities
- `evidence-table-extraction`: Covers deterministic extraction of experiment datasets, metrics, sample sizes, baseline/ablation signals, and evidence-table support snippets from paper Markdown.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/argupaper/extraction/structured.py`, `src/argupaper/chains/evidence.py`, and report-visible evidence output.
- Affected docs: `docs/SMOKE.md` and `docs/DONE.md`.
- Public CLI behavior: `argupaper analyze` should produce denser Evidence Table content for papers with recognizable experiment sections.
- No breaking changes and no dependency changes.
- Rollback strategy: revert this change to restore the previous allowlist-only extraction behavior.
