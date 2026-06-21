## ADDED Requirements

### Requirement: Convert supports non-recursive folder input

The system SHALL allow users to run `argupaper convert --folder <dir>` or `argupaper convert -d <dir>` to convert all direct PDF files in the folder through the existing PDF conversion pipeline.

#### Scenario: Folder conversion processes direct PDFs

- **WHEN** a user runs `argupaper convert --folder ./papers`
- **THEN** the system MUST inspect only direct entries in `./papers`
- **AND** direct `.pdf` files MUST be converted or loaded from cache
- **AND** subdirectories MUST NOT be traversed

#### Scenario: Folder option keeps force compatibility

- **WHEN** a user runs `argupaper convert -d ./papers --force`
- **THEN** the system MUST force reconversion for eligible PDF files
- **AND** `-f` MUST remain the short option for `--force`

### Requirement: Convert validates input mode clearly

The system SHALL require exactly one convert input mode: a single PDF path or a folder path.

#### Scenario: Missing input is rejected

- **WHEN** a user runs `argupaper convert`
- **THEN** the command MUST fail with a readable message explaining that a PDF path or `--folder` is required

#### Scenario: Duplicate input modes are rejected

- **WHEN** a user runs `argupaper convert ./paper.pdf --folder ./papers`
- **THEN** the command MUST fail with a readable message explaining that PDF and folder inputs are mutually exclusive

#### Scenario: Output export is rejected in folder mode

- **WHEN** a user runs `argupaper convert --folder ./papers --output out.md`
- **THEN** the command MUST fail with a readable message explaining that `--output` is only supported for single-file conversion

### Requirement: Folder conversion skips invalid entries and continues after failures

The system SHALL skip non-PDF files, directories, and unreadable direct entries while continuing the batch.

#### Scenario: Non-PDF and directory entries are skipped

- **WHEN** a folder contains `paper.pdf`, `notes.txt`, and a `nested/` directory
- **THEN** the command MUST attempt conversion for `paper.pdf`
- **AND** it MUST skip `notes.txt` and `nested/` with visible reasons

#### Scenario: One PDF failure does not abort the batch

- **WHEN** one eligible PDF fails conversion
- **THEN** the command MUST record that file as failed
- **AND** continue processing remaining eligible PDFs
- **AND** print a final summary including failed count

### Requirement: Folder conversion is visible and traceable

The system SHALL display folder conversion progress and write a durable JSONL trace log for each folder run.

#### Scenario: Folder conversion prints summary and log path

- **WHEN** a folder conversion finishes
- **THEN** the CLI MUST print total entries, success count, cache-hit count, failure count, skipped count, and the log path

#### Scenario: Folder conversion writes JSONL events

- **WHEN** a folder conversion runs
- **THEN** the system MUST write `run_start`, `file_skipped`, `file_success`, `file_failed`, and `run_summary` events as applicable to `data/convert_runs/<run-id>.jsonl`
- **AND** events MUST include the run id, timestamp, status, input path, and relevant cache or error details
