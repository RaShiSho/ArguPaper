## ADDED Requirements

### Requirement: Agent tools use a unified registry
The system SHALL expose Agent-callable tools through `argupaper.tools` rather than chat-private tool implementations.

#### Scenario: Chat builds tools from shared registry
- **WHEN** `argupaper chat` starts
- **THEN** the chat runtime MUST build its toolbox through the shared `argupaper.tools` registry/factory

#### Scenario: Future tools have a single registration path
- **WHEN** a new Agent-callable tool is added
- **THEN** it SHOULD be registered through `argupaper.tools` rather than `argupaper.agents.chat`

### Requirement: Tool registry supports LangChain argument schemas
The system SHALL allow registered tools to carry argument schemas and SHALL adapt them to LangChain structured tools.

#### Scenario: ReAct prompt sees registered tools
- **WHEN** the chat agent prepares ReAct tool descriptions
- **THEN** descriptions MUST be generated from the unified registry-backed toolbox

#### Scenario: Tool errors are normalized
- **WHEN** a tool name is unknown or a tool raises an exception
- **THEN** the toolbox MUST return a structured observation with `tool`, `ok`, `summary`, `data`, and `warnings`

### Requirement: Chat paper tools preserve local-library behavior
The system SHALL preserve the current chat local-library tool behavior after moving implementations to `argupaper.tools`.

#### Scenario: Slash papers lists local records
- **WHEN** a user enters `/papers`
- **THEN** chat MUST still call `list_papers` and return saved PaperStore records

#### Scenario: Natural-language local search uses loose matching
- **WHEN** a user asks to find local papers with a mixed query such as `agent安全`
- **THEN** `list_papers` MUST use loose keyword matching and respect the requested limit

### Requirement: Existing workflows remain tool dependencies only
The system SHALL keep existing workflows as callable tool dependencies without moving chat orchestration into workflows.

#### Scenario: Analyze tool calls AnalyzeWorkflow
- **WHEN** chat requests paper analysis
- **THEN** the tool MUST call `AnalyzeWorkflow` rather than duplicate analysis logic

#### Scenario: External search tool calls search workflow
- **WHEN** chat requests external paper search
- **THEN** the tool MUST call the existing search workflow wrapper
