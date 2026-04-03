# TOON Format Specification Reference

## Overview

**TOON (Token-Oriented Object Notation)**
**Version**: 3.0
**Media Type**: `text/toon`
**File Extension**: `.toon`
**Encoding**: UTF-8
**License**: MIT (Open Source)

## Design Philosophy

TOON is "a compact, human-readable encoding of the JSON data model that minimizes tokens." It achieves efficiency by:

1. **Declaring structure once**: Field headers defined upfront, not repeated
2. **Indentation over braces**: YAML-style nesting instead of `{}`
3. **Tabular data**: CSV-style rows for uniform arrays
4. **Explicit clarity**: `[N]` length and `{fields}` headers improve LLM parsing

## Core Syntax

### Primitives

```toon
# Strings (unquoted unless containing special chars)
name: Alice

# Numbers
age: 42
pi: 3.14159

# Booleans
active: true
disabled: false

# Null
value: null
```

### Objects

```toon
# Simple object
user:
  id: 123
  name: Alice
  role: admin

# Equivalent JSON:
{
  "user": {
    "id": 123,
    "name": "Alice",
    "role": "admin"
  }
}
```

### Uniform Arrays (TOON's Sweet Spot)

```toon
# Array with uniform structure
users[3]{id,name,role}:
1,Alice,admin
2,Bob,user
3,Charlie,viewer

# Equivalent JSON (51 tokens):
{
  "users": [
    {"id": 1, "name": "Alice", "role": "admin"},
    {"id": 2, "name": "Bob", "role": "user"},
    {"id": 3, "name": "Charlie", "role": "viewer"}
  ]
}

# TOON: 24 tokens (53% reduction)
```

### Non-Uniform Arrays

```toon
# Array with mixed items (fallback to JSON-like)
items[3]:
  - {id: 1, name: "Widget"}
  - {id: 2, name: "Gadget", category: "electronics"}
  - "simple string"
```

### Nested Structures

```toon
# Combining uniform arrays with nesting
organization:
  name: Acme Corp
  departments[2]{id,name,headcount}:
  1,Engineering,50
  2,Sales,30
  metadata:
    created: 2024-01-15
    updated: 2025-11-26
```

## Syntax Elements

| Element | Purpose | Example |
|---------|---------|---------|
| `[N]` | Array length declaration | `users[5]` |
| `{field1,field2}` | Field headers | `{id,name,email}` |
| `:` | Separator after declaration | `users[2]{id,name}:` |
| `,` | Field value separator | `1,Alice,alice@example.com` |
| Indentation | Nesting (2 spaces or tab) | (see examples above) |
| `-` | List item marker (non-uniform) | `- item1` |

## Advanced Features

### Optional Fields

```toon
# Some rows may have empty values
users[3]{id,name,email,phone}:
1,Alice,alice@example.com,555-1234
2,Bob,bob@example.com,
3,Charlie,charlie@example.com,555-5678
```

### Escaped Values

```toon
# Values with commas or special chars use quotes
products[2]{id,name,description}:
1,Widget,"Small, efficient gadget"
2,Gadget,"Multi-purpose tool, batteries included"
```

### Inline Uniform Values

```toon
# Single-row uniform data can be inlined (shorthand for a 1-row table)
by_severity{BLOCKER,CRITICAL,MAJOR,MINOR,INFO}: 1,1,1,1,1
by_type{BUG,CODE_SMELL}: 2,3
```

### Mixed Nesting

```toon
# Tabular data with nested metadata
dataset:
  metadata:
    version: 1.0
    source: production
  records[1000]{timestamp,user_id,action,duration_ms}:
  2025-11-26T10:00:00Z,42,login,145
  2025-11-26T10:01:23Z,43,search,89
  # ... 998 more rows
```

## Conversion Examples

### Example 1: Sonar Issues

**JSON (580 tokens):**
```json
{
  "project_key": "cuioss_cui-http-client",
  "pull_request_id": "123",
  "issues": [
    {
      "key": "AX-001",
      "type": "BUG",
      "severity": "BLOCKER",
      "file": "src/main/java/de/cuioss/http/HttpClient.java",
      "line": 145,
      "rule": "java:S2095",
      "message": "Use try-with-resources or close this 'InputStream' in a 'finally' clause.",
      "effort": "10min"
    },
    {
      "key": "AX-002",
      "type": "CODE_SMELL",
      "severity": "MAJOR",
      "file": "src/main/java/de/cuioss/http/HttpClient.java",
      "line": 89,
      "rule": "java:S1192",
      "message": "Define a constant instead of duplicating this literal 'application/json' 4 times.",
      "effort": "5min"
    }
  ],
  "statistics": {
    "total_issues_fetched": 2,
    "by_severity": {
      "BLOCKER": 1,
      "MAJOR": 1
    }
  }
}
```

**TOON (240 tokens - 59% reduction):**
```toon
project_key: cuioss_cui-http-client
pull_request_id: 123

issues[2]{key,type,severity,file,line,rule,message,effort}:
AX-001,BUG,BLOCKER,src/main/java/de/cuioss/http/HttpClient.java,145,java:S2095,"Use try-with-resources or close this 'InputStream' in a 'finally' clause.",10min
AX-002,CODE_SMELL,MAJOR,src/main/java/de/cuioss/http/HttpClient.java,89,java:S1192,"Define a constant instead of duplicating this literal 'application/json' 4 times.",5min

statistics:
  total_issues_fetched: 2
  by_severity:
    BLOCKER: 1
    MAJOR: 1
```

### Example 2: Coverage Analysis

**JSON (520 tokens):**
```json
{
  "status": "success",
  "data": {
    "by_file": [
      {
        "file": "/src/utils/validator.js",
        "lines": 87.5,
        "statements": 88.89,
        "functions": 100,
        "branches": 80,
        "status": "good"
      },
      {
        "file": "/src/utils/formatter.js",
        "lines": 80,
        "statements": 80,
        "functions": 87.5,
        "branches": 66.67,
        "status": "acceptable"
      }
    ]
  }
}
```

**TOON (210 tokens - 60% reduction):**
```toon
status: success

data:
  by_file[2]{file,lines,statements,functions,branches,status}:
  /src/utils/validator.js,87.5,88.89,100,80,good
  /src/utils/formatter.js,80,80,87.5,66.67,acceptable
```

## Implementation Support

### Internal Module (plan-marshall)

The plan-marshall marketplace includes an internal `toon_parser.py` module for TOON serialization:

**Location**: `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py`

**Functions**:
- `parse_toon(content: str) -> dict` - Parse TOON content to Python dict
- `serialize_toon(data: dict, indent: int = 2) -> str` - Serialize Python dict to TOON

**Import Pattern** (from marketplace scripts):
```python
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]
```

Note: The `type: ignore` comment is needed because PYTHONPATH is set at runtime by the executor.

### Usage Example

```python
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Python dict to TOON
data = {
    "status": "success",
    "users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"}
    ]
}

toon_output = serialize_toon(data)
# status: success
# users[2]{id,name,role}:
# 1,Alice,admin
# 2,Bob,user

print(toon_output)
```

## Best Practices

### DO Use TOON For:
PASS Uniform arrays (database results, log entries)
PASS LLM prompts with structured data
PASS Agent tool outputs with repeated structure
PASS Cost-sensitive API calls
PASS Semi-structured data (mix of tabular + nested)

### DON'T Use TOON For:
FAIL API interchange (use JSON)
FAIL Configuration files (use YAML/JSON)
FAIL Deeply nested structures (>3 levels)
FAIL Non-uniform object shapes
FAIL Pure flat tables (use CSV instead)

### Optimization Tips

1. **Group by structure**: Put similar objects in uniform arrays
2. **Flatten when possible**: Reduce nesting depth
3. **Use short field names**: `id` not `identifier` (in headers)
4. **Consistent ordering**: Same field order across rows
5. **Validate structure**: Use `[N]` declarations to help LLM catch errors

## Performance Characteristics

### Token Efficiency
- **Uniform arrays**: 50-60% reduction vs JSON
- **Mixed structures**: 30-40% reduction vs JSON
- **Nested objects**: 20-30% reduction vs JSON
- **Non-uniform data**: May be worse than JSON

### LLM Parsing
- **Schema clarity**: Explicit `[N]` and `{fields}` headers improve parsing accuracy
- **Structural validation**: Declared lengths help LLMs detect malformed data

### Trade-offs
- **Overhead**: ~5-10% vs pure CSV for tabular data
- **Parsing time**: Negligible (microseconds)
- **Learning curve**: Moderate (familiar to JSON/CSV users)

## Specification Status

**Current**: Version 3.0 (Stable). Internal to plan-marshall marketplace.

## Comparison Quick Reference

| Aspect | JSON | TOON | CSV | YAML |
|--------|------|------|-----|------|
| **Token Efficiency** | Baseline | 30-60% reduction | ~70% reduction | ~15% reduction |
| **Nesting Support** | Full | Full | None | Full |
| **Uniform Arrays** | Verbose | Optimal | Compact | Verbose |
| **Non-uniform Data** | Good | OK | Poor | Good |
| **Tooling Support** | Universal | Growing | Universal | Wide |
| **API Compatibility** | Standard | Needs conversion | Limited | Some |
| **Human Readable** | OK | Good | OK | Excellent |
| **Schema Clarity** | Implicit | Explicit | None | Implicit |
