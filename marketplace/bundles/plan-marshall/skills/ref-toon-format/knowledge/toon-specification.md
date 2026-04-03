# TOON Format Specification and Patterns

## Overview

**TOON (Token-Oriented Object Notation)**
**Media Type**: `text/toon` | **File Extension**: `.toon` | **Encoding**: UTF-8

TOON is a compact, human-readable encoding of the JSON data model optimized for LLM token efficiency. It achieves 30-60% token reduction for uniform arrays by declaring structure once and using CSV-style rows.

**Scope**: Internal plan-marshall marketplace operations only — agent-to-agent handoffs, memory persistence, inter-agent data exchange, and test fixtures.

**NOT For**: API interchange (use JSON), configuration files (use YAML/JSON), deeply nested structures (>3 levels), non-uniform object shapes.

## Core Syntax

### Primitives

```toon
name: Alice
age: 42
pi: 3.14159
active: true
disabled: false
value: null
```

### Objects

```toon
user:
  id: 123
  name: Alice
  role: admin
```

### Uniform Arrays (TOON's Sweet Spot)

```toon
users[3]{id,name,role}:
1,Alice,admin
2,Bob,user
3,Charlie,viewer
```

Equivalent JSON (51 tokens) vs TOON (24 tokens) = 53% reduction.

### Non-Uniform Arrays

```toon
items[3]:
  - {id: 1, name: "Widget"}
  - {id: 2, name: "Gadget", category: "electronics"}
  - "simple string"
```

### Nested Structures

```toon
organization:
  name: Acme Corp
  departments[2]{id,name,headcount}:
  1,Engineering,50
  2,Sales,30
  metadata:
    created: 2024-01-15
```

## Syntax Elements

| Element | Purpose | Example |
|---------|---------|---------|
| `[N]` | Array length declaration | `users[5]` |
| `{field1,field2}` | Field headers | `{id,name,email}` |
| `:` | Separator after declaration | `users[2]{id,name}:` |
| `,` | Field value separator | `1,Alice,alice@example.com` |
| Indentation | Nesting (2 spaces) | (see examples above) |
| `-` | List item marker (non-uniform) | `- item1` |
| `\|` | Multi-line value indicator | `description: \|` |
| `#` | Comment | `# This is a comment` |

## Advanced Features

### Optional Fields and Escaped Values

```toon
products[2]{id,name,description}:
1,Widget,"Small, efficient gadget"
2,Gadget,
```

### Inline Uniform Values

```toon
by_severity{BLOCKER,CRITICAL,MAJOR,MINOR,INFO}: 1,1,1,1,1
by_type{BUG,CODE_SMELL}: 2,3
```

## Conversion Example: Sonar Issues

**JSON (580 tokens):**
```json
{
  "project_key": "cuioss_cui-http-client",
  "issues": [
    {"key": "AX-001", "type": "BUG", "severity": "BLOCKER", "file": "HttpClient.java", "line": 145, "rule": "java:S2095", "message": "Use try-with-resources"},
    {"key": "AX-002", "type": "CODE_SMELL", "severity": "MAJOR", "file": "HttpClient.java", "line": 89, "rule": "java:S1192", "message": "Define constant"}
  ]
}
```

**TOON (240 tokens — 59% reduction):**
```toon
project_key: cuioss_cui-http-client

issues[2]{key,type,severity,file,line,rule,message}:
AX-001,BUG,BLOCKER,HttpClient.java,145,java:S2095,Use try-with-resources
AX-002,CODE_SMELL,MAJOR,HttpClient.java,89,java:S1192,Define constant
```

## Agent Handoff Patterns

### Minimal Handoff (~40 tokens)

```toon
from_agent: quality-agent
to_agent: fix-agent

items[3]{file,line}:
A.java,42
B.java,89
C.java,15
```

### Standard Handoff (~140 tokens, 50% reduction vs JSON)

```toon
from_agent: quality-agent
to_agent: verify-agent

context:
  task: Fix code quality issues
  files_analyzed: 15

issues[2]{file,line,severity,rule,message}:
Example.java,42,BLOCKER,S2095,Use try-with-resources
Service.java,89,MAJOR,S1192,Define constant

instructions[2]:
- Start with BLOCKER severity
- Run tests after fixes
```

### Receiving TOON Handoff (Agent Prompt Pattern)

```
You are receiving a handoff from {previous_agent}.

The data uses TOON format:
- Arrays: arrayName[N]{field1,field2}:
- Rows: CSV-style values

---
{toon_data}
---

Process and {action}.
```

## Implementation

### Internal Parser Module

**Location**: `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py`

**Functions**:
- `parse_toon(content: str) -> dict` — Parse TOON content to Python dict
- `serialize_toon(data: dict, indent: int = 2) -> str` — Serialize Python dict to TOON
- `parse_toon_table(content: str, key: str, null_markers: set[str] | None = None) -> list[dict]` — Extract a uniform array table

**Import Pattern** (from marketplace scripts):
```python
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]
```

### Known Limitations

- **Indentation**: Only 2-space indentation is supported (not tabs or 4-space)
- **Percentage values**: `'95%'` is parsed as `95` (int) — lossy round-trip
- **[N] count**: The parser does not validate that declared row count matches actual rows

## Performance Characteristics

| Data Type | Token Reduction vs JSON |
|-----------|----------------------|
| Uniform arrays | 50-60% |
| Mixed structures | 30-40% |
| Nested objects | 20-30% |

## Best Practices

1. **Group by structure**: Put similar objects in uniform arrays
2. **Flatten when possible**: Reduce nesting depth
3. **Use short field names**: `id` not `identifier` (in headers)
4. **Consistent ordering**: Same field order across rows
5. **Validate structure**: Use `[N]` declarations to help LLM catch errors
