## ADDED Requirements

### Requirement: Respond node generates observation-grounded answers
The system SHALL allow the chat `respond` node to generate a final user-facing answer from tool observations using the configured default LLM provider.

#### Scenario: Paper context is explained
- **WHEN** a natural-language turn successfully calls `read_paper_context`
- **THEN** the final response MUST explain the paper from the returned context rather than returning only the tool summary

#### Scenario: Existing final response is preserved
- **WHEN** a previous graph node already produced `final_response`
- **THEN** the `respond` node MUST return that response without invoking the responder LLM

### Requirement: Respond node falls back safely
The system SHALL preserve deterministic observation formatting when responder LLM generation is unavailable or fails.

#### Scenario: Responder provider unavailable
- **WHEN** observations exist but the default LLM provider is unavailable
- **THEN** the final response MUST fall back to the existing observation summary and MUST NOT fail the turn

#### Scenario: Responder call fails
- **WHEN** the responder LLM raises an error or returns empty text
- **THEN** the runtime MUST log the failure and return the existing observation summary

### Requirement: ReAct invalid output can recover with observations
The system SHALL route ReAct invalid JSON failures to `respond` when useful observations already exist.

#### Scenario: ReAct fails after context read
- **WHEN** ReAct cannot parse the next model response after a successful tool observation
- **THEN** the graph MUST route to `respond` and generate or fall back to an answer from the observations

### Requirement: Slash command output remains deterministic
The system SHALL keep slash command responses stable unless they already opted into a final response.

#### Scenario: Papers command remains direct
- **WHEN** a user enters `/papers`
- **THEN** the response SHOULD remain the deterministic local paper list summary
