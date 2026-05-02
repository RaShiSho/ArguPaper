## Context

The current Evidence Table is sparse because experiment extraction only recognizes a small list of common datasets and generic metrics. Real papers often mention domain-specific datasets, benchmark suites, result tables, and metrics with variants such as EM, mAP, AUROC, MAE, NDCG, or ROUGE-L, so `EvidenceChain` frequently receives empty `datasets` and `metrics`.

## Goals / Non-Goals

**Goals:**
- Extract datasets, metrics, sample sizes, baseline, ablation, and result snippets deterministically from paper Markdown.
- Produce Evidence Table rows that include concrete support snippets from experiment-related sections.
- Preserve the existing analyze workflow and report contract: `EvidenceChain` returns dictionaries, `ReportGenerator` renders those rows, and `AnalyzeWorkflow` only propagates warnings.

**Non-Goals:**
- No new LLM call, model prompt, external API, or dependency.
- No full table parser for arbitrary PDF table layouts.
- No redesign of `ResearchReport` or CLI output shape.

## Decisions

- Use section-aware extraction in `StructuredExtractor`: collect text from headings containing experiment, evaluation, result, benchmark, dataset, metric, or empirical keywords. This keeps extraction local to the PDF-derived Markdown and avoids putting heuristics in `AnalyzeWorkflow`.
- Combine curated terms with pattern-based extraction: retain expanded allowlists for common benchmarks/metrics, then add regex patterns for capitalized dataset names, benchmark suites, acronym metrics, and “on <dataset>” / “using <dataset>” phrasing. This is more robust than hard-coded lists alone while still deterministic.
- Build Evidence Table rows in `EvidenceChain` from dataset/metric pairs and support snippets. If multiple datasets and metrics exist, rows should be compact and capped to avoid noisy reports.
- Keep failure behavior non-fatal: if no datasets or metrics are found, return the existing weakness messages and an explicit “Not specified” row only when partial evidence exists.

## Risks / Trade-offs

- [Risk] Regex extraction may include false positives such as method names or section titles. → Mitigation: filter common academic words, cap result counts, and prefer experiment-section context over whole-paper context.
- [Risk] Pairing every dataset with every metric may overstate exact alignment. → Mitigation: support snippets indicate the source sentence, and row count is capped.
- [Risk] Very table-heavy Markdown may still lose structure. → Mitigation: extract from nearby sentences and table rows using text snippets, leaving full table parsing for a later change.
