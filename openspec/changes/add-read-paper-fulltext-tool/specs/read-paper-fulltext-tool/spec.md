## ADDED Requirements

### Requirement: Paper fulltext can be read as an Agent tool
The system SHALL provide a shared Agent-callable tool named `read_paper_fulltext` that reads local PaperStore markdown content for one saved paper.

#### Scenario: Full markdown is returned
- **WHEN** `read_paper_fulltext` is called with a valid paper id and no `max_chars`
- **THEN** the tool result MUST include the full `paper.md` markdown in `data.markdown`
- **AND** the result MUST include metadata, character count, local path, hash, and truncation status

#### Scenario: Full markdown is truncated by request
- **WHEN** `read_paper_fulltext` is called with `max_chars`
- **THEN** the returned markdown MUST be limited to that size
- **AND** `data.truncated` MUST indicate whether truncation occurred

#### Scenario: Report is optionally included
- **WHEN** `include_report` is true
- **THEN** the tool result MAY include report text and MUST include report character count when available

### Requirement: Chat can use selected paper for fulltext reads
The system SHALL allow chat runtime to call `read_paper_fulltext` without explicit `paper_id` when a selected paper exists.

#### Scenario: Selected paper is injected
- **WHEN** the user has selected a paper and the Agent calls `read_paper_fulltext` without `paper_id`
- **THEN** the runtime MUST inject the selected paper id into the tool arguments

### Requirement: Fulltext observations are not persisted raw
The system SHALL redact raw fulltext content from chat runtime JSONL logs.

#### Scenario: Tool observation is logged
- **WHEN** a `read_paper_fulltext` observation is written to the chat log
- **THEN** the logged observation MUST NOT include raw `markdown` or raw `report`
- **AND** it MUST preserve metadata needed for debugging, including length, path, hash, and truncation status

### Requirement: CLI responses avoid fulltext dumps
The system SHALL avoid printing complete paper markdown in final chat responses by default.

#### Scenario: User asks to return full text
- **WHEN** the user asks for the full text of a selected paper
- **THEN** the final response SHOULD provide the local paper path, character count, and status rather than dumping the entire markdown

#### Scenario: User asks for detailed explanation
- **WHEN** the user asks for a detailed explanation based on the full paper
- **THEN** the Agent MAY use fulltext observations to generate a detailed grounded explanation
