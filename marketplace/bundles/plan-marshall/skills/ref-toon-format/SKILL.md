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
| `scripts/toon_parser.py` | TOON parsing and serialization. The public surface is the module's `__all__` — `ToonParseError`, `parse_toon`, `parse_toon_table`, `serialize_toon`, `value_needs_quoting` — and `__all__` is the authority when this list and the module disagree. |

`value_needs_quoting` reports whether the serializer is OBLIGED to wrap a value in
outer double quotes. A consumer that must decide whether a quote it is looking at
could have come from `serialize_toon` consults this predicate rather than
re-deriving the rule, so both sides of that decision stay in one place.

### Known Limitations

- Only 2-space indentation is supported (not tabs or 4-space)
- Percentage values (`'95%'`) are parsed as int (`95`) — lossy round-trip
- The parser does not validate `[N]` count against actual rows

### Related Skills
- `plan-marshall:shared-workflow-helpers` — Shared workflow infrastructure (triage helpers, CLI construction, error codes)
- `plan-marshall:ref-workflow-architecture` — Architecture documentation including workflow skill conventions
