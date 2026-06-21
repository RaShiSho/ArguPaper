## 1. Cache Lookup Foundation

- [x] 1.1 Add MarkdownCache record lookup helpers for cache key, original filename, and filename stem; verifiable by inspecting returned candidate metadata and content paths.
- [x] 1.2 Define readable cache miss and ambiguous-match error messages that include the suggested `argupaper convert <pdf>` next step or candidate cache keys.

## 2. Workflow Decoupling

- [x] 2.1 Extend AnalyzeOptions so analyze can receive either a legacy PDF path or a cached Markdown identity; verifiable by constructing options for both paths.
- [x] 2.2 Refactor AnalyzeWorkflow into Markdown input loading and Markdown analysis stages; verifiable because cached Markdown analysis does not invoke PDFPipeline.
- [x] 2.3 Preserve legacy PDF path behavior with a warning recommending `convert -> analyze <paper-name>`.

## 3. CLI Surface

- [x] 3.1 Add `argupaper convert <pdf> [--force] [--output]`; verifiable via `uv run argupaper convert --help`.
- [x] 3.2 Update `argupaper analyze <paper>` so non-path input resolves cached Markdown by name; verifiable via `uv run argupaper analyze "sample"`.
- [x] 3.3 Register the new command and keep Web analyze upload compatible with the legacy PDF path.

## 4. Documentation and Smoke

- [x] 4.1 Update README with the recommended `convert -> analyze <paper-name>` workflow.
- [x] 4.2 Update `docs/SMOKE.md` with convert success, cached analyze success, missing cache, ambiguous cache, and legacy PDF scenarios.
- [x] 4.3 Update `docs/DONE.md` with a concise completion note.

## 5. Verification

- [x] 5.1 Run `uv run python -m compileall src/argupaper`.
- [x] 5.2 Run `uv run argupaper --help`, `uv run argupaper convert --help`, and `uv run argupaper analyze --help`.
- [x] 5.3 Run `openspec status --change "separate-pdf-convert-and-name-analyze"` and confirm artifacts are apply-ready.
