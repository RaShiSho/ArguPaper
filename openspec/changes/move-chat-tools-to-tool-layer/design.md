## Context

The LangGraph chat runtime should remain responsible for conversation state and graph execution. Tool implementation belongs in `argupaper.tools`, where other agent runtimes can reuse the same wrappers for PaperStore and workflows.

## Goals / Non-Goals

**Goals:**

- Make `argupaper.tools` the single registration layer for Agent-callable tools.
- Preserve current chat behavior and local-library loose keyword search.
- Keep existing workflows as the business logic owners.
- Provide a LangChain adapter that normalizes unknown tools, exceptions, and result envelopes.

**Non-Goals:**

- Do not add PaperMemoryIndex or vector retrieval.
- Do not rewrite `AnalyzeWorkflow`, `InteractiveSearchWorkflow`, `PapersWorkflow`, or PaperStore behavior.
- Do not change the LangGraph node structure.

## Decisions

- `ToolResult` is the common observation envelope and includes `tool`, `ok`, `summary`, `data`, and `warnings`.
- Tool argument schemas live in `argupaper.tools.schemas` so registry entries can expose them to LangChain.
- `ToolRegistry` stores `args_schema` beside each callable.
- `LangChainToolbox` adapts registry entries into `StructuredTool` instances and centralizes unknown-tool and exception handling.
- `build_default_tool_registry(config, progress_callback)` registers paper and workflow tools in one place.
- `argupaper.agents.chat.tools` remains as a compatibility wrapper, but chat graph imports the default toolbox from `argupaper.tools`.

## Risks / Trade-offs

- Moving code can accidentally change observations; keep summaries and data keys compatible with existing chat formatting.
- Some tools call external services; verification should focus on local PaperStore tools plus help/compile checks, with external search kept as manual smoke.
- The compatibility wrapper avoids breaking older imports but should not grow new behavior.
