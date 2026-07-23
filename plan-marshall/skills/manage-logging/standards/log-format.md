# Log Format Specification

This document defines the standard log entry format used by the unified logging infrastructure.

## Standard Entry Format

```text
[{timestamp}] [{level}] [{hash}] {message}
  {field}: {value}
  ...
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `timestamp` | ISO 8601 UTC timestamp | `2025-12-11T12:14:26Z` |
| `level` | Log severity level | `INFO`, `WARNING`, `ERROR` |
| `hash` | 6-character hash computed from message content | `a3f2c1` |
| `message` | Primary log message | `plan-marshall:manage-files add (0.15s)` |
| `field: value` | Additional data (indented) | `phase: 1-init` |

The hash provides deterministic traceability — the same message always produces the same hash, enabling cross-stage linking (analysis → resolution → Q-gate). Callers never need to compute hashes; they are generated automatically.

---

## Timestamp Format

> Timestamps use the standard format. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) § Timestamp Format.

---

## Indented Fields

Additional data is provided as indented key-value pairs:

```text
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

```text
[2025-12-11T12:14:26Z] [INFO] [{hash}] {notation} {subcommand} ({duration}s)
```

**Example**:
```text
[2025-12-11T12:14:26Z] [INFO] [a3f2c1] plan-marshall:manage-files:manage-files create-or-reference (0.19s)
```

### Error Entry

```text
[2025-12-11T12:17:50Z] [ERROR] [{hash}] {notation} {subcommand} ({duration}s)
  exit_code: {code}
  args: {full_args}
  stderr: {truncated_stderr}
```

**Example**:
```text
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

```text
[{timestamp}] [{level}] [{hash}] {message}
```

Work log messages embed the category in the message text as `[CATEGORY] (caller) description`. The third bracket position is always the auto-generated hash ID.

### Entry Types by Category

#### PROGRESS

```text
[2025-12-11T11:14:30Z] [INFO] [c8d3e2] [PROGRESS] (plan-marshall:phase-1-init) Starting 1-init phase
```

#### ARTIFACT

```text
[2025-12-11T11:15:24Z] [INFO] [f1a9b3] [ARTIFACT] (plan-marshall:phase-1-init) Created plan: Migrate agent outputs to TOON
```

##### Extended caller for phase-5-execute task artifacts

The ARTIFACT category supports a single sanctioned **three-segment caller form** used exclusively by `plan-marshall:phase-5-execute` when logging file-system artifacts produced while executing a specific task:

```text
(plan-marshall:phase-5-execute:{task_number})
```

**Rationale**: Retrospective consumers and audit tooling need to group artifact writes by task without cross-correlating timestamps against `TASK-*.json` step windows. Embedding `{task_number}` directly in the caller segment turns task-level grouping into a trivial prefix match on the work-log stream, eliminating a brittle join step.

**Message shapes**: Only three shapes are sanctioned under this extended caller — all follow the pattern `{Verb} {path}` (or `{Verb} {old} -> {new}` for renames):

```text
[2025-12-11T11:20:01Z] [INFO] [a1b2c3] [ARTIFACT] (plan-marshall:phase-5-execute:4) Wrote marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md
```

```text
[2025-12-11T11:20:02Z] [INFO] [d4e5f6] [ARTIFACT] (plan-marshall:phase-5-execute:4) Deleted marketplace/bundles/plan-marshall/skills/legacy-skill/SKILL.md
```

```text
[2025-12-11T11:20:03Z] [INFO] [g7h8i9] [ARTIFACT] (plan-marshall:phase-5-execute:4) Renamed marketplace/bundles/plan-marshall/skills/old-name -> marketplace/bundles/plan-marshall/skills/new-name
```

**Scope restriction**: This is the **only** sanctioned three-segment caller in the logging system. All other skills — including other `phase-*` skills, `manage-*` scripts, recipes, and user workflows — MUST continue to use the standard two-segment `(bundle:skill)` caller shape documented throughout this specification. Introducing additional three-segment callers would undermine the prefix-match grouping contract that retrospective consumers rely on.

#### ERROR

```text
[2025-12-11T11:17:50Z] [ERROR] [d4a1c7] [ERROR] (plan-marshall:phase-3-outline) Skill load failed
```

#### OUTCOME

```text
[2025-12-11T11:17:55Z] [INFO] [e5c7d4] [OUTCOME] (plan-marshall:phase-3-outline) Impact analysis complete: 19 agents identified
```

#### FINDING

```text
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

```text
[{timestamp}] [{level}] [{hash}] (caller) {message}
```

### Examples

```text
[2025-12-11T11:14:48Z] [INFO] [d2e8f1] (plan-marshall:phase-1-init) Detected domain: java - pom.xml found
```

```text
[2025-12-11T11:20:15Z] [INFO] [a4b6c8] (pm-plugin-development:ext-outline-workflow) Scope: bundles=all
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `phase` | Yes | Current workflow phase |
| `detail` | No | Additional context or reasoning |

---

## Orchestrator Logged Events

**Files**: `.plan/local/orchestrator/{slug}/logs/work.log` and `.plan/local/orchestrator/{slug}/logs/decision.log` (written via `--store orchestrator` on the `work` / `decision` verbs; main-anchored, no global fallback).

Entries use the standard entry format and the standard two-segment `(bundle:skill)` caller shape. Exactly four event types are defined for the orchestrator store:

| Event | Verb / File | Category bracket | Purpose |
|-------|-------------|------------------|---------|
| decision | `decision` → `decision.log` | none (file is the category) | Orchestration decisions (decomposition, queue ordering, fold/park calls) |
| interaction | `work` → `work.log` | `[INTERACTION]` | AskUserQuestion outcomes — the question topic and the operator's chosen option |
| plan-status-change | `work` → `work.log` | `[PLAN-STATUS]` | A tracked plan's lifecycle transition in the epic queue |
| reconciliation | `work` → `work.log` | `[RECONCILIATION]` | Ledger reconciliation — landing reports folded into epic.md / status.json |

One example line per event type:

```text
[2026-07-16T10:02:11Z] [INFO] [b3c9e4] (plan-marshall:marshall-orchestrator) Decomposed epic into 3 workstreams: WS-01-substrate, WS-02-surface, WS-03-ship
```

```text
[2026-07-16T10:05:42Z] [INFO] [a7d2f8] [INTERACTION] (plan-marshall:marshall-orchestrator) AskUserQuestion: PLAN-03 ordering -> operator chose "park until PLAN-01 lands"
```

```text
[2026-07-16T10:41:07Z] [INFO] [c4e8a1] [PLAN-STATUS] (plan-marshall:marshall-orchestrator) PLAN-02 queued -> running
```

```text
[2026-07-16T11:20:33Z] [INFO] [e9f1b6] [RECONCILIATION] (plan-marshall:marshall-orchestrator) Folded landing report landings/PLAN-01.md into epic.md queue; retired 2 folded queue items
```

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

| Log Type | Plan-Scoped | Global | Orchestrator (`--store orchestrator`) |
|----------|-------------|--------|----------------------------------------|
| Script Execution | `logs/script-execution.log` | `script-execution-YYYY-MM-DD.log` | — (not store-aware) |
| Work | `logs/work.log` | `work-YYYY-MM-DD.log` | `.plan/local/orchestrator/{slug}/logs/work.log` |
| Decision | `logs/decision.log` | `decision-YYYY-MM-DD.log` | `.plan/local/orchestrator/{slug}/logs/decision.log` |

---

## Encoding

- File encoding: UTF-8
- Line endings: LF (Unix-style)
- No BOM
