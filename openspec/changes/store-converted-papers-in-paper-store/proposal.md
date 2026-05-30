## Why

`argupaper convert` currently stores Markdown only in `MarkdownCache`, while `argupaper papers` and the Web Library only see records created by `analyze`. This makes converted-but-not-yet-analyzed papers invisible from the local library even though their Markdown already exists; fixing this now improves the core reading workflow before adding larger agent or knowledge-graph capabilities.

## What Changes

- Persist successful convert results into `PaperStore` using the existing cache key as `paper_id`.
- Add a mutually exclusive `library_status` metadata field:
  - `converted` for PDF -> Markdown records without analysis report.
  - `analyzed` for records saved by the analyze workflow.
- Treat legacy PaperStore records without `library_status` as `analyzed` when reading.
- Display `library_status` in `argupaper papers` and the Web Library list/detail views.
- Update smoke documentation and completed-work notes for the new library behavior.

## Capabilities

### New Capabilities
- `paper-store-converted-records`: Covers PaperStore persistence for convert results, status semantics, CLI/Web display, and backward compatibility.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `PaperStore` gains converted-record persistence and status normalization.
  - `ConvertWorkflow` writes to PaperStore after successful single or folder conversion.
  - `AnalyzeWorkflow` saves analyzed status when it writes reports.
  - CLI formatters and Web Library show the new status.
- Public interface impact:
  - PaperStore metadata includes optional `library_status` with values `converted` or `analyzed`.
  - Existing CLI and Web API arguments remain unchanged.
- Rollback strategy:
  - Remove the converted-record save call from `ConvertWorkflow`.
  - Remove status display additions from CLI/Web.
  - Leave existing PaperStore directories and metadata files in place; they remain readable as normal saved records.
