## ADDED Requirements

### Requirement: PDF conversion is available as a standalone CLI command
The system SHALL provide a standalone `argupaper convert <pdf>` command that converts a local PDF to Markdown and stores the result in the existing Markdown cache.

#### Scenario: Convert stores Markdown in cache
- **WHEN** a user runs `argupaper convert ./paper.pdf`
- **THEN** the system MUST run the PDF conversion pipeline, write the Markdown cache entry and metadata, and display the cache key plus whether the result came from cache

#### Scenario: Convert optionally exports Markdown
- **WHEN** a user runs `argupaper convert ./paper.pdf --output ./paper.md`
- **THEN** the system MUST also write the converted Markdown to the requested output path

### Requirement: Analyze can run from cached Markdown by paper name
The system SHALL allow `argupaper analyze <paper-name>` to locate a unique cached Markdown entry by original PDF filename, filename stem, or cache key and run the existing analysis stages without calling MinerU.

#### Scenario: Analyze uses cached Markdown
- **WHEN** a cache entry exists for `sample.pdf` and the user runs `argupaper analyze sample`
- **THEN** the system MUST load the cached Markdown and complete structured analysis, evidence checks, debate, judge, report generation, and PaperStore persistence without submitting a PDF conversion task

#### Scenario: Analyze reports missing cache entry
- **WHEN** no cache entry matches the provided paper name
- **THEN** the system MUST fail with a readable message that instructs the user to run `argupaper convert <pdf>` first

#### Scenario: Analyze rejects ambiguous cache matches
- **WHEN** multiple cache entries match the provided paper name
- **THEN** the system MUST fail with a readable message listing candidate original filenames and cache keys instead of choosing one automatically

### Requirement: Analyze retains legacy PDF input compatibility
The system SHALL continue to accept an existing local `.pdf` path for `argupaper analyze`, but this path is considered a compatibility path and MUST emit a migration warning.

#### Scenario: Analyze accepts legacy PDF path
- **WHEN** a user runs `argupaper analyze ./paper.pdf`
- **THEN** the system MUST convert or read the PDF through the existing pipeline, complete analysis, and include a warning recommending `argupaper convert ./paper.pdf` followed by `argupaper analyze paper`

### Requirement: Web analyze remains compatible
The local Web workbench SHALL continue to accept uploaded PDFs and run analysis through the legacy PDF path.

#### Scenario: Web upload still analyzes PDF
- **WHEN** the Web workbench submits a local PDF upload to `/api/analyze`
- **THEN** the backend MUST continue creating an analyze job that processes the uploaded PDF without requiring a separate Web convert step
