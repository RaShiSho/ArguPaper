## ADDED Requirements

### Requirement: Chat prioritizes local PaperStore for local paper content requests
The system SHALL route natural-language local paper content requests to PaperStore-backed tools before external search unless the user explicitly asks for external search.

#### Scenario: Named local paper content request
- **WHEN** a user asks `帮我看看 BackdoorAgent 这篇论文讲了什么`
- **THEN** the chat runtime MUST first attempt `select_paper` with `paper=BackdoorAgent`
- **AND** it MUST NOT call `search_papers` before local selection has failed or the user explicitly requested external search

#### Scenario: Selected paper content request
- **WHEN** a paper is already selected and the user asks about `这篇论文`
- **THEN** the chat runtime MUST first call `read_paper_context` for the selected paper

#### Scenario: Local library search request
- **WHEN** a user asks to find papers in the local paper library
- **THEN** the chat runtime MUST call `list_papers` with a local query and requested limit when they can be extracted

### Requirement: Tool prompts expose exact schemas
The system SHALL expose registered tool argument schemas to the chat ReAct prompt.

#### Scenario: ReAct sees legal argument names
- **WHEN** the chat runtime builds a ReAct prompt
- **THEN** the tool section MUST include each tool name, description, argument fields, and required fields

### Requirement: Tool argument aliases are normalized before validation
The system SHALL normalize common LLM-generated aliases before invoking registered tools.

#### Scenario: Select paper query alias
- **WHEN** ReAct emits `select_paper` with `{"query": "BackdoorAgent"}`
- **THEN** the runtime MUST invoke the tool with `{"paper": "BackdoorAgent"}`

#### Scenario: Paper context paper alias
- **WHEN** ReAct emits `read_paper_context` with `{"paper": "<paper_id>"}`
- **THEN** the runtime MUST invoke the tool with `{"paper_id": "<paper_id>"}`

### Requirement: Repeated identical tool calls are blocked
The system SHALL prevent exact duplicate tool calls within one chat turn from repeatedly executing.

#### Scenario: Duplicate failed tool call
- **WHEN** a tool call signature has already failed in the current turn
- **AND** ReAct emits the same tool and normalized arguments again
- **THEN** the runtime MUST block the duplicate, log `duplicate_tool_call_blocked`, add a warning, and converge without executing the tool again

#### Scenario: Duplicate successful tool call
- **WHEN** a tool call signature has already succeeded in the current turn
- **AND** ReAct emits the same tool and normalized arguments again
- **THEN** the runtime MUST block the duplicate, log `duplicate_tool_call_blocked`, and converge without executing the tool again
