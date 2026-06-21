## ADDED Requirements

### Requirement: Convert persists browseable PaperStore records
The system SHALL save every successful PDF conversion into PaperStore using the conversion cache key as the paper ID.

#### Scenario: Single-file convert saves a converted record
- **WHEN** a user runs `argupaper convert ./paper.pdf`
- **THEN** the system MUST store the converted Markdown in MarkdownCache
- **AND** save a PaperStore record with `library_status` set to `converted`
- **AND** `argupaper papers` MUST list that record

#### Scenario: Folder convert saves each successful PDF
- **WHEN** a user runs `argupaper convert --folder ./papers`
- **THEN** each successfully converted PDF MUST create or update a PaperStore record with `library_status` set to `converted`
- **AND** failed or skipped entries MUST keep the existing per-file batch behavior

#### Scenario: Cache hit still syncs PaperStore
- **WHEN** a conversion is loaded from MarkdownCache
- **THEN** the system MUST still ensure a matching PaperStore record exists

### Requirement: Analyze upgrades converted records to analyzed
The system SHALL mark records saved by analysis as analyzed.

#### Scenario: Analyze runs after convert
- **WHEN** a converted record exists for a paper
- **AND** the user runs analyze for the same cached paper
- **THEN** the PaperStore record MUST be updated with `library_status` set to `analyzed`
- **AND** the record MUST contain the analysis report and structured summary

### Requirement: Paper library displays record status
The system SHALL expose converted/analyzed status in local library views.

#### Scenario: CLI lists statuses
- **WHEN** a user runs `argupaper papers`
- **THEN** each row MUST display the record's `library_status`

#### Scenario: CLI detail displays status
- **WHEN** a user runs `argupaper papers <paper_id>`
- **THEN** the detail view MUST display the record's `library_status`

#### Scenario: Web Library displays status
- **WHEN** the Web Library lists or opens saved records
- **THEN** it MUST display the record's `library_status`

### Requirement: Legacy records remain readable
The system SHALL treat existing PaperStore records without `library_status` as analyzed.

#### Scenario: Existing analyzed record has no status metadata
- **WHEN** PaperStore reads a record whose metadata lacks `library_status`
- **THEN** the returned metadata MUST include `library_status` set to `analyzed`
