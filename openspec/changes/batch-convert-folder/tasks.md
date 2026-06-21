## 1. OpenSpec

- [x] 1.1 Create `batch-convert-folder` change scaffold.
- [x] 1.2 Add proposal, design, tasks, and spec artifacts for folder conversion.

## 2. CLI Behavior

- [x] 2.1 Make `convert` accept either optional `pdf` or `--folder/-d`, with clear mutually-exclusive validation.
- [x] 2.2 Preserve single-file conversion behavior, including `--output/-o` and `--force/-f`.
- [x] 2.3 Implement non-recursive folder scanning with skip handling for directories, non-PDF files, and unreadable entries.
- [x] 2.4 Continue after individual PDF conversion failures and print a final summary.

## 3. Trace Logging

- [x] 3.1 Create per-run JSONL logs under `data/convert_runs/`.
- [x] 3.2 Log run start, skipped entries, successes, failures, and final summary with traceable paths.

## 4. Documentation

- [x] 4.1 Update README with folder conversion examples and logging behavior.
- [x] 4.2 Update `docs/SMOKE.md` with folder conversion smoke coverage.
- [x] 4.3 Update `docs/DONE.md` with a concise completion note.

## 5. Verification

- [x] 5.1 Run `uv run python -m compileall src/argupaper`.
- [x] 5.2 Run `uv run argupaper convert --help`.
- [x] 5.3 Run input validation commands for missing input, duplicate inputs, folder `--output`, and missing folder.
- [x] 5.4 Run `openspec status --change "batch-convert-folder"` and confirm artifacts are apply-ready.
