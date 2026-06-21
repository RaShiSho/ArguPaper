## ADDED Requirements

### Requirement: Analyze debate uses LangChain-backed role chains
The system SHALL use LangChain prompt and runnable composition as the primary implementation for Support and Skeptic debate roles in the analyze workflow.

#### Scenario: Configured default LLM generates debate messages
- **WHEN** the default LLM provider is configured and `argupaper analyze` reaches the debate stage
- **THEN** Support and Skeptic messages MUST be produced through LangChain-backed role chains while preserving the existing `DebateState` and `AgentMessage` output structure

### Requirement: Debate fallback preserves analyze completion
The system SHALL preserve deterministic role fallback behavior when LangChain or the default LLM provider is unavailable, fails, or returns empty content.

#### Scenario: Missing or failed LLM falls back
- **WHEN** the debate role chain cannot produce usable output because the LLM provider is missing, raises an error, or returns empty content
- **THEN** the system MUST produce a fallback Support or Skeptic message and include a warning that explains the fallback reason

### Requirement: Debate configuration and early-stop behavior remain compatible
The system SHALL keep the current debate round ordering, `DEBATE_MAX_ROUNDS` compatibility, and early-stop behavior after moving role generation to LangChain.

#### Scenario: Existing round controls still apply
- **WHEN** `DEBATE_MAX_ROUNDS` or analyze `--rounds` sets the maximum debate rounds
- **THEN** the debate MUST run Support before Skeptic each round, stop no later than the configured maximum, and still stop early when the current early-consensus conditions are met

### Requirement: Analyze workflow warning propagation remains explicit
The system SHALL propagate debate role fallback warnings into the final analyze workflow warnings before report generation.

#### Scenario: Debate warning appears in analyze result
- **WHEN** a Support or Skeptic role falls back during analyze
- **THEN** the final `AnalyzeWorkflowResult.warnings` MUST include the debate fallback warning so CLI and Web users can see that the report used degraded debate output

### Requirement: Search Agent remains outside the LangChain debate refactor
The system SHALL NOT change Search Agent parsing, clarification, retrieval, filtering, or trace persistence behavior as part of this analyze debate refactor.

#### Scenario: Search workflow remains unchanged
- **WHEN** a user runs `argupaper search`
- **THEN** the command MUST continue using the existing SearchAgentWorkflow behavior and MUST NOT require the new analyze debate adapter
