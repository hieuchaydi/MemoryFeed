# MCP RAG Integration

This guide documents the MemoryFeed MCP retrieval tool designed for direct LLM context injection.

## Goal

Use MemoryFeed as a retrieval layer in agent workflows without building custom response formatters.

## Tool

`build_memory_context(query, limit=8, days_back=None, max_context_chars=4000)`

## Response Contract

- `query`: original query string
- `count`: number of citations included in `context`
- `context`: prompt-ready plain text with numbered entries
- `citations`: structured references for traceability
- `truncated`: `true` when not all retrieved rows were included
- `limit_applied`: server-side bounded limit after MCP policy clamp
- `max_context_chars_applied`: bounded context budget after clamp
- `meta.requested_results`: number of search rows returned before context filtering
- `meta.kept_results`: rows included in output context
- `meta.skipped_empty`: rows dropped because they had no text content
- `meta.dropped_by_budget`: rows excluded due to context budget
- `meta.context_char_budget`: final char budget used to build context

## Bounded Defaults

- `limit` is clamped by MCP policy and a hard cap of `20`.
- `max_context_chars` is clamped to `500..16000`.
- Per-row text is normalized and truncated for stable context shaping.

## Example MCP Call

```json
{
  "tool": "build_memory_context",
  "arguments": {
    "query": "what did we decide about sqlcipher migration",
    "limit": 8,
    "days_back": 30,
    "max_context_chars": 3000
  }
}
```

## Example LLM Prompt Wiring

```text
You are helping with implementation decisions.
Use only facts from the memory context below.
If unsure, say you are unsure.

Memory context:
{{memory_context.context}}

Question:
{{user_question}}
```

## Citation Usage

- Render footnotes from `citations`.
- Persist `citations` in trace logs for auditability.
- Use `source_index` to map citations back to original retrieval ordering.

## Phase 2 Hardening Notes

- Citation ranks are contiguous even when some raw rows are skipped.
- Source URLs are normalized to remove newline/whitespace artifacts.
- Context assembly returns explicit truncation metadata for easier debugging.
