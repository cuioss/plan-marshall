# Log Format Specification

This document defines the standard log entry format used by the unified logging infrastructure.

## Standard Entry Format

```
[{timestamp}] [{level}] [{category}] {message}
  {field}: {value}
  ...
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `timestamp` | ISO 8601 UTC timestamp | `2025-12-11T12:14:26Z` |
| `level` | Log severity level | `INFO`, `WARN`, `ERROR` |
| `category` | Entry categorization | `SCRIPT`, `DECISION`, `ARTIFACT` |
| `message` | Primary log message | `pm-workflow:manage-files add (0.15s)` |
| `field: value` | Additional data (indented) | `phase: 1-init` |

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
[2025-12-11T12:14:26Z] [ERROR] [SCRIPT] pm-workflow:manage-log add (0.16s)
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
[2025-12-11T12:14:26Z] [INFO] [SCRIPT] {notation} {subcommand} ({duration}s)
```

**Example**:
```
[2025-12-11T12:14:26Z] [INFO] [SCRIPT] pm-workflow:manage-files:manage-files create-or-reference (0.19s)
```

### Error Entry

```
[2025-12-11T12:17:50Z] [ERROR] [SCRIPT] {notation} {subcommand} ({duration}s)
  exit_code: {code}
  args: {full_args}
  stderr: {truncated_stderr}
```

**Example**:
```
[2025-12-11T12:17:50Z] [ERROR] [SCRIPT] pm-workflow:manage-log:manage-work-log add (0.16s)
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
[{timestamp}] [{level}] [{category}] {message}
  phase: {phase}
  [detail: {detail}]
```

### Entry Types by Category

#### PROGRESS

```
[2025-12-11T11:14:30Z] [INFO] [PROGRESS] Starting 1-init phase
  phase: 1-init
```

#### ARTIFACT

```
[2025-12-11T11:15:24Z] [INFO] [ARTIFACT] Created plan: Migrate agent outputs to TOON
  phase: 1-init
  detail: Source: description, domain: plan-marshall-plugin-dev
```

#### ERROR

```
[2025-12-11T11:17:50Z] [ERROR] [ERROR] Skill load failed
  phase: 3-outline
  detail: plugin-solution-outline skill not found in references.json
```

#### OUTCOME

```
[2025-12-11T11:17:55Z] [INFO] [OUTCOME] Impact analysis complete: 19 agents identified
  phase: 3-outline
  detail: Categories: 3 builder, 9 Java, 2 JS, 3 plan-marshall-plugin-dev, 2 workflow
```

#### FINDING

```
[2025-12-11T11:17:48Z] [INFO] [FINDING] Affected: gradle-builder.md
  phase: 3-outline
  detail: Agent returns JSON output in Step 4. Should be migrated to TOON format.
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `phase` | Yes | Current workflow phase |
| `detail` | No | Additional context or reasoning |

---

## Decision Log Format

**File**: `decision.log`

Decision entries are written to a dedicated log file. They do NOT include a `[DECISION]` category prefix since the file itself indicates the entry type.

### Standard Entry

```
[{timestamp}] [{level}] {message}
  phase: {phase}
  [detail: {detail}]
```

### Examples

```
[2025-12-11T11:14:48Z] [INFO] (pm-workflow:phase-1-init) Detected domain: java - pom.xml found
  phase: 1-init
```

```
[2025-12-11T11:20:15Z] [INFO] (pm-plugin-development:ext-outline-plugin) Scope: bundles=all
  phase: 3-outline
  detail: marketplace/bundles structure detected
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
^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] \[(\w+)\] \[(\w+)\] (.+)$
```

**Field pattern**:
```regex
^  (\w+): (.+)$
```

### Python Example

```python
import re

HEADER_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] '
    r'\[(\w+)\] \[(\w+)\] (.+)$'
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
                'category': header_match.group(3),
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
