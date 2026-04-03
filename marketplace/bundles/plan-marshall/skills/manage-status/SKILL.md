---
name: manage-status
description: Manage status.json files with phase tracking and metadata
user-invocable: false
scope: plan
---

# Manage Status Skill

Manage status.json files with phase tracking and metadata. Handles plan status storage (JSON), phase operations, and metadata management.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify status.json directly; all mutations go through the script API
- Do not invent script arguments not listed in the Operations table
- Do not set invalid phase status values (only pending, in_progress, done)

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-status:manage_status {command} {args}`
- Note: Script filename uses underscore (`manage_status`) unlike other manage-* skills that use hyphens
- Phase transitions must use `set-phase` or `update-phase` commands
- Metadata operations require explicit `--get` or `--set` flags

## What This Skill Provides

- Read/write status.json (JSON storage, TOON output)
- Phase lifecycle management (set, update, progress)
- Metadata key-value storage
- Combined context retrieval

## When to Activate This Skill

Activate this skill when:
- Creating plan status during initialization
- Updating phase progress
- Storing or retrieving metadata (change_type, etc.)
- Getting combined status context

---

## Storage Location

Status is stored in the plan directory:

```
.plan/plans/{plan_id}/status.json
```

---

## File Format

JSON format for storage:

```json
{
  "title": "Plan Title",
  "current_phase": "1-init",
  "phases": [
    {"name": "1-init", "status": "in_progress"},
    {"name": "2-refine", "status": "pending"},
    {"name": "3-outline", "status": "pending"},
    {"name": "4-plan", "status": "pending"},
    {"name": "5-execute", "status": "pending"},
    {"name": "6-finalize", "status": "pending"}
  ],
  "metadata": {
    "change_type": "feature"
  },
  "created": "2025-01-15T10:00:00Z",
  "updated": "2025-01-15T14:30:00Z"
}
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Plan title |
| `current_phase` | string | Current active phase |
| `phases` | list | Phase objects with name and status |
| `metadata` | table | Key-value metadata (common fields: `change_type`, `confidence`, `domain`) |
| `created` | string | ISO timestamp of creation |
| `updated` | string | ISO timestamp of last update |

### Phase Status Values

| Status | Description |
|--------|-------------|
| `pending` | Phase not yet started |
| `in_progress` | Phase currently active |
| `done` | Phase completed |

---

## Operations

Script: `plan-marshall:manage-status:manage_status`

### create

Create status.json with initial phases.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status create \
  --plan-id {plan_id} \
  --title {title} \
  --phases {comma-separated-phases} \
  [--force]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--title` (required): Plan title
- `--phases` (required): Comma-separated phase names in execution order (e.g., `1-init,2-refine,3-outline,4-plan,5-execute,6-finalize`). Order matters — it determines progress calculation and transition sequence.
- `--force`: Overwrite existing status.json

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: status.json
created: true
plan:
  title: My Feature
  current_phase: 1-init
```

### read

Read entire status.json content.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
plan:
  title: My Feature
  current_phase: 2-refine
  phases: [...]
  metadata: {...}
```

### set-phase

Set current phase (marks phase as in_progress).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status set-phase \
  --plan-id {plan_id} \
  --phase {phase_name}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
current_phase: 2-refine
previous_phase: 1-init
```

### update-phase

Update a specific phase's status.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status update-phase \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --status {pending|in_progress|done}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
phase: 1-init
phase_status: done
```

### progress

Calculate plan progress percentage.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status progress \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
progress:
  total_phases: 6
  completed_phases: 3
  current_phase: 4-plan
  percent: 50
```

**Progress formula**: `percent = floor(completed_phases / total_phases * 100)`. A phase counts as "completed" only when its status is `done`. Phases with status `in_progress` or `pending` are not counted.

### metadata

Get or set metadata fields.

**Set metadata**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field {field_name} \
  --value {value}
```

**Get metadata**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field {field_name}
```

**Output (set)** (TOON):
```toon
status: success
plan_id: my-feature
field: change_type
value: feature
previous_value: bug_fix
```

**Output (get)** (TOON):
```toon
status: success
plan_id: my-feature
field: change_type
value: feature
```

### get-context

Get combined status context (phase, progress, metadata) in one call.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get-context \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
title: My Feature
current_phase: 2-refine
total_phases: 6
completed_phases: 1
change_type: feature
```

**Note**: All metadata fields are promoted to top level for convenience (flattened from `metadata` object). The fields shown depend on what has been set via `metadata --set`.

---

## Scripts

**Script**: `plan-marshall:manage-status:manage_status`

| Command | Parameters | Description |
|---------|------------|-------------|
| `create` | `--plan-id --title --phases [--force]` | Create status.json |
| `read` | `--plan-id` | Read full status |
| `set-phase` | `--plan-id --phase` | Set current phase (marks as in_progress) |
| `update-phase` | `--plan-id --phase --status` | Update specific phase status |
| `progress` | `--plan-id` | Calculate progress percentage |
| `metadata` | `--plan-id --get/--set --field [--value]` | Get/set metadata fields |
| `get-context` | `--plan-id` | Get combined status context |

---

## Error Responses

All errors return TOON with `status: error` and exit code 1, except metadata get on missing field.

| Error Code | Exit Code | Cause |
|------------|-----------|-------|
| `invalid_plan_id` | 1 | Plan ID not in kebab-case format |
| `file_not_found` | 1 | status.json doesn't exist |
| `file_exists` | 1 | status.json already exists (use `--force`) |
| `invalid_phase` | 1 | Phase name not in the phases list |
| `phase_not_found` | 1 | Phase doesn't exist in status.json |
| `not_found` | 0 | Metadata field doesn't exist — valid query result (returns `value: null`), not an error |

```toon
status: error
plan_id: my-feature
error: file_not_found
message: status.json not found
```

---

## Integration Points

### With manage-lifecycle

manage-lifecycle handles phase transitions and routing; manage-status handles status storage and metadata. The `transition` command in manage-lifecycle calls `update-phase` and `set-phase` in manage-status.

### With phase skills

Phase skills read/update status through manage-status:
- phase-1-init: Creates status with `create`
- phase-2-refine onwards: Uses `set-phase`, `metadata`, `get-context`

### With agents

Agents use `metadata` to store change_type and other classification data.

## Related Skills

- `manage-lifecycle` — Delegates to manage-status for phase transitions and storage
- `manage-metrics` — Augments phase tracking with timing and token data
- `manage-config` — System configuration consumed by status operations
