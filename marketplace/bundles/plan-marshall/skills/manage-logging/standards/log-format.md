# Log Format Specification

This document defines the standard log entry format used by the unified logging infrastructure.

## Standard Entry Format

```
[{timestamp}] [{level}] [{hash}] {message}
  {field}: {value}
  ...
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `timestamp` | ISO 8601 UTC timestamp | `2025-12-11T12:14:26Z` |
| `level` | Log severity level | `INFO`, `WARN`, `ERROR` |
| `hash` | 6-character hash computed from message content | `a3f2c1` |
| `message` | Primary log message | `plan-marshall:manage-files add (0.15s)` |
| `field: value` | Additional data (indented) | `phase: 1-init` |

The hash provides deterministic traceability — the same message always produces the same hash, enabling cross-stage linking (analysis → resolution → Q-gate). Callers never need to compute hashes; they are generated automatically.

---

## Timestamp Format

All timestamps use ISO 8601 format in UTC timezone:

```
YYYY-MM-DDTHH:MM:SSZ
```

**Examples**:
- `2025-12-11T12:14:26Z`
- `2025-12-11T00:00:00Z`

**Rules**:
- Always UTC (Z suffix)
- No milliseconds (seconds precision)
- No timezone offset notation

---

## Indented Fields

Additional data is provided as indented key-value pairs:

```
[2025-12-11T12:14:26Z] [ERROR] [b7e4d9] plan-marshall:manage-logging:manage-logging add (0.16s)
  exit_code: 2
  args: add --plan-id test --phase 3-outline
  stderr: error: invalid argument
```

**Rules**:
- Two-space indentation
- Format: `{key}: {value}`
- One field per line
- Values may contain spaces
- No nested fields

---

## Script Execution Log Format

**File**: `script-execution.log`

### Success Entry

```
[2025-12-11T12:14:26Z] [INFO] [{hash}] {notation} {subcommand} ({duration}s)
```

**Example**:
```
[2025-12-11T12:14:26Z] [INFO] [a3f2c1] plan-marshall:manage-files:manage-files create-or-reference (0.19s)
```

### Error Entry

```
[2025-12-11T12:17:50Z] [ERROR] [{hash}] {notation} {subcommand} ({duration}s)
  exit_code: {code}
  args: {full_args}
  stderr: {truncated_stderr}
```

**Example**:
```
[2025-12-11T12:17:50Z] [ERROR] [b7e4d9] plan-marshall:manage-logging:manage-logging add (0.16s)
  exit_code: 2
  args: add --plan-id test --phase 3-outline --type milestone
  stderr: error: argument --type: invalid choice: 'milestone'
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `notation` | Yes | Script notation (bundle:skill:script) |
| `subcommand` | Yes | Script subcommand |
| `duration` | Yes | Execution time in seconds |
| `exit_code` | Error only | Process exit code |
| `args` | Error only | Full argument list |
| `stdout` | Error only | Truncated stdout (if relevant) |
| `stderr` | Error only | Truncated stderr |

---

## Work Log Format

**File**: `work.log`

### Standard Entry

```
[{timestamp}] [{level}] [{hash}] {message}
```

Work log messages embed the category in the message text as `[CATEGORY] (caller) description`. The third bracket position is always the auto-generated hash ID.

### Entry Types by Category

#### PROGRESS

```
[2025-12-11T11:14:30Z] [INFO] [c8d3e2] [PROGRESS] (plan-marshall:phase-1-init) Starting 1-init phase
```

#### ARTIFACT

```
[2025-12-11T11:15:24Z] [INFO] [f1a9b3] [ARTIFACT] (plan-marshall:phase-1-init) Created plan: Migrate agent outputs to TOON
```

#### ERROR

```
[2025-12-11T11:17:50Z] [ERROR] [d4a1c7] [ERROR] (plan-marshall:phase-3-outline) Skill load failed
```

#### OUTCOME

```
[2025-12-11T11:17:55Z] [INFO] [e5c7d4] [OUTCOME] (plan-marshall:phase-3-outline) Impact analysis complete: 19 agents identified
```

#### FINDING

```
[2025-12-11T11:17:48Z] [INFO] [b2f8a3] [FINDING] (plan-marshall:phase-3-outline) Affected: gradle-builder.md
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `phase` | Yes | Current workflow phase |
| `detail` | No | Additional context or reasoning |

---

## Decision Log Format

**File**: `decision.log`

Decision entries are written to a dedicated log file. They do NOT include a `[DECISION]` category prefix since the file itself indicates the entry type. The format uses `(caller)` prefix in the message to identify the source skill.

### Standard Entry

```
[{timestamp}] [{level}] [{hash}] (caller) {message}
```

### Examples

```
[2025-12-11T11:14:48Z] [INFO] [d2e8f1] (plan-marshall:phase-1-init) Detected domain: java - pom.xml found
```

```
[2025-12-11T11:20:15Z] [INFO] [a4b6c8] (pm-plugin-development:ext-outline-workflow) Scope: bundles=all
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `phase` | Yes | Current workflow phase |
| `detail` | No | Additional context or reasoning |

---

## Parsing Guidelines

### Reading Log Files

1. Split file by lines
2. Identify entry start: line begins with `[`
3. Parse header: extract timestamp, level, category, message
4. Collect indented fields until next entry or EOF

### Regular Expressions

**Header pattern**:
```regex
^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] \[(\w+)\] \[([a-f0-9]{6})\] (.+)$
```

**Field pattern** (for script execution error entries with indented fields):
```regex
^  (\w+): (.+)$
```

### Python Example

```python
import re

HEADER_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] '
    r'\[(\w+)\] \[([a-f0-9]{6})\] (.+)$'
)
FIELD_PATTERN = re.compile(r'^  (\w+): (.+)$')

def parse_log_file(content: str) -> list[dict]:
    entries = []
    current = None

    for line in content.split('\n'):
        header_match = HEADER_PATTERN.match(line)
        if header_match:
            if current:
                entries.append(current)
            current = {
                'timestamp': header_match.group(1),
                'level': header_match.group(2),
                'hash_id': header_match.group(3),
                'message': header_match.group(4),
                'fields': {}
            }
        elif current:
            field_match = FIELD_PATTERN.match(line)
            if field_match:
                current['fields'][field_match.group(1)] = field_match.group(2)

    if current:
        entries.append(current)

    return entries
```

---

## File Naming

All plan-scoped logs are stored in the `logs/` subdirectory of the plan.

| Log Type | Plan-Scoped | Global |
|----------|-------------|--------|
| Script Execution | `logs/script-execution.log` | `script-execution-YYYY-MM-DD.log` |
| Work | `logs/work.log` | `work-YYYY-MM-DD.log` |
| Decision | `logs/decision.log` | `decision-YYYY-MM-DD.log` |

---

## Encoding

- File encoding: UTF-8
- Line endings: LF (Unix-style)
- No BOM
