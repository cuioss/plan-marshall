---
name: ref-toon-format
description: TOON format knowledge and usage patterns for agent communication and memory persistence in plan-marshall marketplace
user-invocable: false
---

# TOON Format Usage Skill

**REFERENCE MODE**: This skill provides TOON format reference material. Load specific references on-demand based on current task.

Pure reference skill providing TOON (Token-Oriented Object Notation) format specification and usage patterns for agent handoffs and memory persistence.

## Enforcement

**Execution mode**: Reference library with parser module; load references on-demand, import parser as documented.

**Prohibited actions:**
- Do not load all references at once; load progressively based on current task
- Do not use TOON for external APIs or configuration files
- Do not bypass `toon_parser.py` with custom parsing logic

**Constraints:**
- TOON is only for internal plan-marshall marketplace operations
- Length declarations `[N]` must match actual row counts
- Field headers `{fields}` must match all rows
- Import parser via `from toon_parser import parse_toon, serialize_toon`

## Core Concepts

TOON (Token-Oriented Object Notation) is a compact, human-readable encoding of the JSON data model that minimizes tokens.

**Key Features**: 30-60% token reduction vs JSON for uniform arrays. Declared structure once — field headers defined upfront, not repeated. CSV-style rows for uniform arrays. Explicit `[N]` length and `{fields}` headers improve LLM parsing.

**Best For**: Agent handoffs with uniform issue lists, coverage reports, build failures, memory persistence.

**NOT For**: API interchange (use JSON), configuration files (use YAML/JSON), deeply nested structures (>3 levels), non-uniform object shapes.

**Scope**: TOON is ONLY for internal plan-marshall marketplace operations — agent-to-agent handoffs, memory persistence, inter-agent data exchange, and test fixtures.

## Available References

Load the reference matching your current task:

### 1. TOON Specification (Technical Reference)
**File**: `knowledge/toon-specification.md`

**Load When**: Learning TOON syntax, understanding conversion patterns, validating TOON structure, comparing with JSON/CSV/YAML.

**Contents**: Core syntax, uniform arrays, nested structures, advanced features, conversion examples, `toon_parser.py` usage, best practices, performance characteristics.

### 2. Agent Patterns (Usage Patterns)
**File**: `knowledge/agent-patterns.md`

**Load When**: Creating agent handoff templates, designing memory persistence, converting JSON fixtures to TOON, understanding agent prompt patterns.

**Contents**: Handoff templates, memory persistence patterns, agent prompt patterns, test fixture examples, token impact measurements, migration guidance.

## Shared Infrastructure

This skill also hosts shared Python modules used across workflow scripts:

| Module | Purpose |
|--------|---------|
| `scripts/toon_parser.py` | TOON parsing and serialization (`parse_toon`, `serialize_toon`, `parse_toon_table`) |
| `scripts/triage_helpers.py` | Shared workflow utilities: CLI boilerplate, error taxonomy, TOON output, priority calculation, triage handlers |

`triage_helpers.py` lives here because all its output flows through `print_toon()` / TOON serialization, making this the natural home for the shared output layer. Other exports (`create_workflow_cli`, `ErrorCode`, `is_test_file`, `calculate_priority`, triage command handlers) are co-located to avoid fragmenting a cohesive utility module.

## Resources

- TOON Specification: https://github.com/toon-format/spec
- TOON Playground: https://toon-format.github.io/playground

### Related Skills
- `plan-marshall:ref-workflow-architecture` — Architecture documentation including workflow skill conventions
