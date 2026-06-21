## Why

`argupaper convert` can only process one local PDF per invocation, which makes batch conversion of a paper folder tedious and hard to audit. Adding a folder mode now improves the PDF-to-Markdown preparation workflow without expanding the downstream analyze/debate scope.

## What Changes

- Add `argupaper convert --folder <dir>` / `argupaper convert -d <dir>` for non-recursive folder conversion.
- Keep `--force/-f` as the existing force-reconvert option; `-f` is not repurposed for folders.
- Require exactly one input source: either a single `pdf` argument or `--folder`.
- Reject `--output` in folder mode because per-file export paths are intentionally out of scope.
- Skip non-PDF files, directories, and unreadable entries while continuing the batch.
- Continue after individual PDF conversion failures and report a final summary.
- Persist per-run JSONL trace logs under `data/convert_runs/`.
- Update README, `docs/SMOKE.md`, and `docs/DONE.md`.

## Capabilities

### New Capabilities

- `batch-convert-folder`: Defines CLI folder conversion, skip/failure handling, progress visibility, and trace logging for PDF-to-Markdown batch runs.

### Modified Capabilities

- None.

## Impact

- CLI: `convert` gains a folder option while existing single-file usage remains compatible.
- PDF pipeline: no behavior change; folder mode reuses the existing `PDFPipeline.process()` sequentially.
- Storage: adds JSONL run logs under `data/convert_runs/`; existing Markdown cache layout remains unchanged.
- Docs: smoke and user-facing examples gain batch conversion coverage.
- Rollback: remove the folder option and batch helper logic from `convert`, delete the new OpenSpec change, and remove the documentation entries. Existing cache files and run logs require no migration.
