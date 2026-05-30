## 1. OpenSpec Artifacts

- [x] 1.1 Create proposal, design, spec, and task artifacts for converted PaperStore records; verifiable with `openspec status --change "store-converted-papers-in-paper-store"`.

## 2. PaperStore Persistence

- [x] 2.1 Add converted-record persistence to PaperStore with `library_status: converted`.
- [x] 2.2 Ensure analyze saves use `library_status: analyzed`.
- [x] 2.3 Normalize missing `library_status` on read as `analyzed`, and include status in simple search text.

## 3. Convert Workflow Integration

- [x] 3.1 Inject/build PaperStore in ConvertWorkflow.
- [x] 3.2 Sync single-file convert success, including cache hits, to PaperStore.
- [x] 3.3 Sync folder convert successes to PaperStore without changing per-file failure semantics.

## 4. Library Display

- [x] 4.1 Show `library_status` in `argupaper papers` list and detail output.
- [x] 4.2 Show `library_status` in Web Library list and detail output.

## 5. Documentation and Verification

- [x] 5.1 Update `docs/DONE.md` with a concise completion note.
- [x] 5.2 Update `docs/SMOKE.md` with converted/analyzed PaperStore scenarios.
- [x] 5.3 Run OpenSpec status and basic CLI/Python validation commands.
