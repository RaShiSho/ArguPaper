## Context

`MarkdownCache` already stores converted Markdown keyed by the PDF hash. `PaperStore` stores local library records under the same kind of stable `paper_id`, but it is currently written only by `AnalyzeWorkflow`. The least disruptive design is to keep MarkdownCache as the conversion cache and use PaperStore as the browseable library projection.

## Goals / Non-Goals

**Goals:**

- Save successful convert results into PaperStore for both single-file and folder conversion.
- Use one mutually exclusive `library_status` value per record.
- Upgrade a converted record to analyzed when analyze later saves the same `paper_id`.
- Keep current CLI and Web API inputs unchanged.

**Non-Goals:**

- Do not add a database, vector index, or migration command.
- Do not add filtering flags to `argupaper papers`.
- Do not add a Web convert page.

## Decisions

- **Use cache key as PaperStore paper_id.** This keeps convert and analyze aligned for the same PDF and avoids filename collision problems.
- **Store status in metadata.** `library_status` belongs with `title`, `source`, and `from_cache`, and can be surfaced without changing the file layout.
- **Normalize missing status on read.** Existing analyzed records were created before this field existed, so `_read_metadata()` will default missing values to `analyzed`.
- **Convert writes lightweight records.** Converted records contain metadata, empty structured summary, Markdown, and an empty report. This makes `argupaper papers <id> --markdown` work immediately while report rendering stays naturally empty.
- **Analyze overwrites status to analyzed.** Existing `save_paper()` remains the analyze persistence path and ensures `library_status` is `analyzed` even if caller metadata omits it.

## Risks / Trade-offs

- A convert cache hit may create a PaperStore record later than the original conversion; this is intentional so the library projection can self-heal.
- Converted records do not have structured summaries, so Library detail summary fields remain empty until analyze runs.
- Folder conversion still uses per-file failure handling; PaperStore write failures for one file should be recorded as that file failure and should not stop the entire folder run.
