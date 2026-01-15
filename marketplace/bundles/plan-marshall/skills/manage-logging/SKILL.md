---
name: manage-logging
description: Unified logging infrastructure for script execution and work progress tracking
allowed-tools: Read, Bash
---

# Logging Skill

Unified logging infrastructure providing script execution logging and semantic work progress tracking.

## Overview

This skill provides a single unified API for two logging concerns:

1. **Script Execution Logging**: Tracking of script executor invocations (type: `script`)
2. **Work Logging**: Semantic tracking of work progress (type: `work`)

## Log Files

### Script Execution Log

**File**: `.plan/plans/{plan-id}/script-execution.log` (plan-scoped)
**Fallback**: `.plan/logs/script-execution-YYYY-MM-DD.log` (global)

### Work Log

**File**: `.plan/plans/{plan-id}/work.log`

---

## CLI Script Usage

Script: `plan-marshall:manage-logging:manage-log`

### Write API (Positional)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  {type} {plan_id} {level} "{message}"
```

**Arguments** (all positional, all required):

| Argument | Values | Description |
|----------|--------|-------------|
| `type` | `script`, `work` | Log type (determines output file) |
| `plan_id` | kebab-case | Plan identifier |
| `level` | `INFO`, `WARN`, `ERROR` | Log level |
| `message` | string | Log message |

**Output**: None (exit code only)

### Read API

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id {plan_id} --type {work|script} [--limit N] [--phase PHASE]
```

**Arguments**:

| Argument | Required | Description |
|----------|----------|-------------|
| `--plan-id` | Yes | Plan identifier |
| `--type` | Yes | Log type: `work` or `script` |
| `--limit` | No | Max entries to return (most recent) |
| `--phase` | No | Filter by phase (work logs only) |

**Output** (TOON):

```toon
status: success
plan_id: my-plan
log_type: work
total_entries: 5
showing: 3

entries:
  - timestamp: 2025-12-11T11:14:30Z
    level: INFO
    category: DECISION
    message: Detected domain: java
    phase: init
  - timestamp: 2025-12-11T11:15:20Z
    level: INFO
    category: ARTIFACT
    message: Created deliverable: auth module
```

### Examples

```bash
# Write: Script execution logging
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  script my-plan INFO "pm-workflow:manage-task:manage-task add (0.15s)"

python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  script my-plan ERROR "pm-workflow:manage-task:manage-task add failed (exit 1)"

# Write: Work logging (include [TAG] (caller) prefix)
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work my-plan INFO "[ARTIFACT] (pm-workflow:phase-1-init) Created deliverable: auth module"

python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work my-plan WARN "[STATUS] (pm-workflow:phase-4-execute) Skipped validation step"

# Read: All work log entries
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id my-plan --type work

# Read: Last 5 work log entries
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id my-plan --type work --limit 5

# Read: Work log entries for 1-init phase only
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id my-plan --type work --phase 1-init
```

---

## Log Format

### Standard Entry Structure

```
[{timestamp}] [{level}] {message}
```

Since entries go to separate files (`script-execution.log` vs `work.log`), redundant type tags are omitted.

### Example Output

**script-execution.log**:
```
[2025-12-11T12:14:26Z] [INFO] pm-workflow:manage-files:manage-files create (0.19s)
[2025-12-11T12:17:50Z] [ERROR] pm-workflow:manage-task:manage-task add failed (exit 1)
```

**work.log**:
```
[2025-12-11T11:14:30Z] [INFO] [STATUS] (pm-workflow:phase-1-init) Starting init phase
[2025-12-11T11:14:48Z] [INFO] [DECISION] (pm-workflow:phase-1-init) Detected domain: java (pom.xml found)
[2025-12-11T11:15:20Z] [INFO] [ARTIFACT] (pm-workflow:phase-1-init) Created deliverable: auth module
```

### Log Levels

| Level | Description |
|-------|-------------|
| `INFO` | Progress, informational, or successful completion message |
| `WARN` | Warning (non-fatal issue) |
| `ERROR` | Error with details |

---

## Python Import (from scripts run via executor)

Scripts run via the executor have PYTHONPATH set up for cross-skill imports:

```python
from plan_logging import log_entry

# Log to global script log
log_entry('script', 'global', 'INFO', '[MY-COMPONENT] Processing started')

# Log to plan-specific log
log_entry('work', 'my-plan', 'INFO', '[ARTIFACT] Created deliverable')
```

**Note**: IDE warnings about unresolved imports are expected - PYTHONPATH is set at runtime by the executor.

---

## Storage Locations

### Plan-Scoped Logs

```
.plan/plans/{plan-id}/
├── script-execution.log    # Script execution tracking
└── work.log                # Work progress tracking
```

### Global Logs

```
.plan/logs/
├── script-execution-YYYY-MM-DD.log    # Daily global script logs
└── work-YYYY-MM-DD.log                # Daily global work logs (when no plan)
```

**Scope Selection**:
- If `plan_id` is provided and plan directory exists: plan-scoped log
- Otherwise: global log (both script and work types supported)

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLAN_BASE_DIR` | Base directory for .plan structure | `.plan` |
| `LOG_MAX_OUTPUT` | Max chars to capture from stdout/stderr | `2000` |
| `LOG_RETENTION_DAYS` | Days to keep global logs | `7` |

---

## Integration Points

### With Script Executor

The executor automatically calls `log_script_execution()` after each script run.

### With Planning Skills

Planning skills call the simplified API:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work my-plan INFO "[ARTIFACT] (pm-workflow:phase-3-plan) Created task: implement auth module"
```

---

## Scripts

| Script | Notation | Description |
|--------|----------|-------------|
| `manage-log.py` | `plan-marshall:manage-logging:manage-log` | CLI for logging operations (write and read) |
| `plan_logging.py` | - | Python module (imported, not executed) |

### Script Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| (positional) | `{type} {plan_id} {level} "{message}"` | Write log entry |
| `read` | `--plan-id --type [--limit] [--phase]` | Read log entries (TOON output) |
