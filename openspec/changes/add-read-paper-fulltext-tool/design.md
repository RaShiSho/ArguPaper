## Design

`read_paper_fulltext` is implemented as a PaperStore-backed tool in the shared tool layer, not as chat-specific business logic. It reads the same local record used by `read_paper_context`, but returns the full `paper.md` markdown by default.

The tool result contains the full markdown in process memory so the responder can synthesize detailed answers. To avoid large persistent logs and terminal dumps, chat runtime redacts `markdown` and `report` fields before writing tool observations to JSONL. The user-facing fallback response is the tool summary, which includes title, character count, path, hash, and truncation status.

The responder prompt is updated to treat fulltext as source material, not instructions. It may summarize or explain the paper but must not paste the full markdown into the CLI response. If the user asks to return the full text, the answer should provide the local file path and metadata instead.

## Decisions

- Fulltext is a new tool, not an option on `read_paper_context`, to preserve lightweight context semantics.
- Default `max_chars` is `None`, so the full markdown is returned to Agent memory unless the caller explicitly limits it.
- Logs never store raw `markdown` or `report` from `read_paper_fulltext`.
- The first implementation does not add chunk or section retrieval; that remains future PaperMemoryIndex work.
