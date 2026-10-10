---
name: ref-toon-format
description: TOON format knowledge and usage patterns for agent communication and memory persistence in plan-marshall marketplace
user-invocable: false
mode: knowledge
---

# TOON Format Reference

**REFERENCE MODE**: Pure reference skill providing TOON (Token-Oriented Object Notation) format specification, usage patterns, and the parser module.

## Enforcement

**Execution mode**: Reference library with parser module; load reference on-demand.

**Prohibited actions:**
- Do not use TOON for external APIs or configuration files
- Do not bypass `toon_parser.py` with custom parsing logic

**Constraints:**
- TOON is only for internal plan-marshall marketplace operations
- Length declarations `[N]` must match actual row counts
- Field headers `{fields}` must match all rows
- Import what you need from `toon_parser` (e.g. `from toon_parser import parse_toon, serialize_toon`); never re-implement a reader or a quoting rule locally

## Reference

**File**: `knowledge/toon-specification.md`

**Contents**: Core syntax, uniform arrays, nested structures, conversion examples, agent handoff patterns, `toon_parser.py` usage, known limitations, performance characteristics, best practices.

## Parser Module

| Module | Purpose |
|--------|---------|
| `scripts/toon_parser.py` | TOON parsing and serialization. The public surface is the module's `__all__` — `SimpleArrayLine`, `ToonParseError`, `block_scalar_body_continues`, `block_scalar_header_indent`, `classify_simple_array_line`, `list_item_min_indent`, `parse_toon`, `parse_toon_table`, `serialize_toon`, `value_needs_quoting` — and `__all__` is the authority when this list and the module disagree. |

Five of those exports exist so a consumer never has to re-derive a decision this
module already makes:

- `value_needs_quoting` reports whether the serializer is OBLIGED to wrap a value
  in outer double quotes. A consumer deciding whether a quote it is looking at
  could have come from `serialize_toon` consults this predicate.
- `list_item_min_indent` reports the minimum indent a row may carry to belong to
  a `key[N]:` header — column 0 for a top-level header, the header's own indent
  for a nested one.
- `classify_simple_array_line` reports one line's role in a list body: an item
  (with its raw, still-quoted text), an ignorable line, or the array's end.
- `block_scalar_header_indent` reports whether a line opens a `key: |` block
  scalar, and at what indent. The key is any text up to the FIRST colon — the
  parser constrains it no further, so `task.name: |` opens a block exactly as
  `description: |` does.
- `block_scalar_body_continues` reports whether a line still belongs to an open
  block's body: blank lines and lines indented deeper than the header do, and the
  first non-blank line at or outside it closes the block.

Those four are boundaries — where a list body begins and ends, and where opaque
prose begins and ends. A caller that walks either for its own purposes —
collecting raw row texts before `parse_toon` unquotes them, or skipping past a
block scalar so a `steps:` sentence inside a description is not read as document
structure — reads it from here, because two readers deriving one boundary two
ways is how a line becomes structure to one and text to the other.

### Known Limitations

- Only 2-space indentation is supported (not tabs or 4-space)
- Percentage values (`'95%'`) are parsed as int (`95`) — lossy round-trip
- The parser does not validate `[N]` count against actual rows

### Related Skills
- `plan-marshall:shared-workflow-helpers` — Shared workflow infrastructure (triage helpers, CLI construction, error codes)
- `plan-marshall:ref-workflow-architecture` — Architecture documentation including workflow skill conventions
