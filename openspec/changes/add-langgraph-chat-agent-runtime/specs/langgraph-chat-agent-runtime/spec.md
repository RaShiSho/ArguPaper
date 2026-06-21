## ADDED Requirements

### Requirement: Chat command uses a LangGraph Agent Runtime
The system SHALL implement `argupaper chat` as a conversation-oriented LangGraph Agent State Graph located under `argupaper.agents.chat`, not as a workflow module.

#### Scenario: Chat starts with agent runtime
- **WHEN** a user runs `argupaper chat`
- **THEN** the command MUST start an interactive CLI shell backed by the LangGraph chat agent runtime

#### Scenario: No chat workflow module
- **WHEN** the chat implementation is inspected
- **THEN** the chat orchestration MUST NOT live in `argupaper.workflows.chat`

### Requirement: Chat state tracks conversation and execution context
The system SHALL keep per-process Agent State for chat turns, selected paper, plans, tool calls, observations, warnings, final response, interruption state, session id, run id, and future memory or multi-agent extension fields.

#### Scenario: Paper selection persists during one process
- **WHEN** a user selects a paper with `/use <paper>`
- **THEN** later turns in the same `argupaper chat` process MUST be able to use that selected paper

### Requirement: Existing workflows are exposed only as tools
The system SHALL expose paper listing, paper selection/context reading, paper analysis, and paper search to chat as structured tools that call existing workflows or PaperStore APIs.

#### Scenario: Papers command uses tool wrapper
- **WHEN** a user enters `/papers`
- **THEN** the chat runtime MUST invoke a workflow-backed tool rather than parsing output from the standalone `argupaper papers` CLI command

#### Scenario: Analyze uses existing workflow
- **WHEN** chat analyzes a selected paper
- **THEN** it MUST call `AnalyzeWorkflow` through a tool wrapper and MUST NOT duplicate analyze business logic

### Requirement: Planner and ReAct tool loop route natural language
The system SHALL use a Planner plus ReAct-style tool loop to handle natural language requests when an LLM provider is available.

#### Scenario: Natural-language search
- **WHEN** a user asks for related papers in natural language
- **THEN** the chat agent MUST be able to plan and call the search tool

#### Scenario: Selected-paper question answering
- **WHEN** a user asks a question about the selected paper
- **THEN** the chat agent MUST be able to read selected-paper context and answer from that context

### Requirement: Slash-command fallback works without LLM
The system SHALL keep slash commands usable when Planner or ReAct LLM calls are unavailable or invalid.

#### Scenario: LLM unavailable
- **WHEN** no suitable LLM provider is configured and the user enters `/papers`, `/use <paper>`, or `/analyze`
- **THEN** the chat runtime MUST execute the corresponding tool-backed action

#### Scenario: Natural language unavailable
- **WHEN** no suitable LLM provider is configured and the user enters natural language
- **THEN** the chat runtime MUST explain that natural-language agent mode is unavailable and list supported slash commands

### Requirement: Chat runtime logs execution audit events
The system SHALL write one JSONL audit log per chat session under the configured chat log path.

#### Scenario: Tool execution is logged
- **WHEN** a chat turn calls a tool
- **THEN** the log MUST include the tool call, observation summary, warnings or errors, and final response summary

#### Scenario: Interruption is logged
- **WHEN** a user interrupts a running task with ESC
- **THEN** the log MUST include an interrupted event for that run
