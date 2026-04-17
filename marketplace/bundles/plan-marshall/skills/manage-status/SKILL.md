---
name: manage-status
description: Manage status.json files with phase tracking, metadata, and lifecycle operations
user-invocable: false
scope: plan
---

# Manage Status Skill

Manage status.json files with phase tracking, metadata, and lifecycle operations. Handles plan status storage (JSON), phase operations, metadata management, plan discovery, phase transitions, archiving, and routing.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid phase status values: `pending`, `in_progress`, `done`
- Script uses underscore (`manage_status`) because it is imported as a Python module by other scripts
- Phase transitions must use `set-phase`, `update-phase`, or `transition` commands
- Metadata operations require explicit `--get` or `--set` flags

**Standards:** See [status-lifecycle.md](standards/status-lifecycle.md) for the phase state machine, plan lifecycle, and metadata conventions.
- Do not skip phase transition validation
- Phase transitions are sequential -- you cannot skip phases
- Routing context is read-only; use `get-routing-context` for combined state

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

### mark-step-done

Record the outcome of a phase step inside `status.metadata.phase_steps`. Phase skills use this to persist intra-phase progress (e.g., discovery, drift-detection) so that resuming a phase can skip completed steps. Outcomes are restricted to `done` or `skipped`. An optional `--display-detail` one-line string is persisted alongside the outcome so downstream renderers (phase-6-finalize vertical-steps block, etc.) can surface user-facing step summaries.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --step {step_id} \
  --outcome {done|skipped} \
  [--display-detail "one-line user-facing detail"] \
  [--force]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase` (required): Phase name (e.g., `5-execute`)
- `--step` (required): Step identifier within the phase (free-form string chosen by the phase skill)
- `--outcome` (required): `done` or `skipped`
- `--display-detail` (optional at CLI level, required-by-convention for phase-6-finalize steps per the phase-6-finalize interface contract): One-line user-facing detail string. Persisted as `null` when omitted.
- `--force` (optional): Overwrite an existing differing outcome

**Storage shape** (breaking — replaces the old bare-string shape):

```json
status.metadata.phase_steps[{phase}][{step}] = {
  "outcome": "done" | "skipped",
  "display_detail": <string> | null
}
```

Both the `metadata` and `phase_steps` containers are created on demand. Bare-string entries from prior versions are treated as drift — see conflict semantics below.

**Semantics**:
- **Idempotent on identical outcome AND display_detail**: If the step already has the requested outcome and the same `display_detail`, no file write occurs and `changed: false` is returned.
- **Detail-only update**: If the outcome matches but `display_detail` differs, the command updates the detail in place and returns `changed: true`.
- **Conflict on differing outcome**: If the step already has a different outcome and `--force` is not supplied, the command returns `error: conflict` with the existing outcome surfaced in the response. Supplying `--force` overwrites the existing value (and detail).
- **Legacy drift rejection**: If the existing entry is a bare string (pre-migration shape), the command returns `error: legacy_string_entry` and refuses to write. The caller must migrate `status.metadata.phase_steps` to the dict shape before retrying — there is no automatic migration.

> **Forward reference — `phase_steps_complete` invariant**: Downstream phase skills and verification helpers treat `status.metadata.phase_steps[{phase}]` as the authoritative record of which intra-phase steps have been marked `done` or `skipped`. A phase is considered `phase_steps_complete` when every step in the phase's declared step list has a dict entry with `outcome == 'done'`. The invariant reader rejects bare-string entries as legacy drift. Consumers must not fabricate entries by other means — always go through `mark-step-done`.

**Output — idempotent no-op** (TOON):
```toon
status: success
plan_id: my-feature
phase: 5-execute
step: discovery
outcome: done
display_detail: null
changed: false
```

**Output — state changed** (TOON):
```toon
status: success
plan_id: my-feature
phase: 5-execute
step: discovery
outcome: done
display_detail: Discovered 3 drift candidates across deliverables 2 and 4
changed: true
previous_outcome: null
previous_display_detail: null
```

**Output — conflict** (TOON):
```toon
status: error
plan_id: my-feature
error: conflict
phase: 5-execute
step: discovery
existing_outcome: skipped
requested_outcome: done
message: Step 'discovery' in phase '5-execute' already marked as 'skipped'; use --force to overwrite with 'done'
```

**Output — legacy drift** (TOON):
```toon
status: error
plan_id: my-feature
error: legacy_string_entry
phase: 5-execute
step: discovery
existing_outcome: done
requested_outcome: done
message: Step 'discovery' in phase '5-execute' has legacy bare-string storage ('done'); migrate status.metadata.phase_steps to the dict shape {"outcome": ..., "display_detail": ...} before retrying.
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

### list

Discover all plans, optionally filtered by current phase.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status list \
  [--filter PHASE]
```

**Parameters**:
- `--filter` (optional): Comma-separated phase names to filter by

**Output** (TOON):
```toon
status: success
total: 2

plans[2]{id,current_phase,status}:
my-feature,3-outline,in_progress
bugfix-123,5-execute,in_progress
```

### transition

Mark a phase as done and advance to next phase. Validates phase ordering.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed {phase_name}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
completed_phase: 3-outline
next_phase: 4-plan
```

### archive

Archive a completed plan (moves to `.plan/archived-plans/YYYY-MM-DD-{plan_id}`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status archive \
  --plan-id {plan_id} \
  [--dry-run]
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
archived_to: .plan/archived-plans/2026-04-02-my-feature
```

### delete-plan

Delete an entire plan directory. Used when user selects "Replace" for an existing plan during plan-init.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status delete-plan \
  --plan-id {plan_id}
```

**Output** (TOON format):

On success:
```toon
status: success
plan_id: my-feature
action: deleted
path: /path/to/.plan/plans/my-feature
files_removed: 5
```

On error (plan not found):
```toon
status: error
plan_id: my-feature
error: plan_not_found
message: Plan directory does not exist: /path/to/.plan/plans/my-feature
```

**Use case**: Called by plan-init when user selects "Replace" to delete existing plan before creating new one. See `plan-marshall:phase-1-init/standards/plan-overwrite.md` for the full workflow.

**Warning**: This recursively deletes the entire plan directory including all subdirectories (logs, tasks, work artifacts). There is no undo.

### route

Get skill name for a phase.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status route \
  --phase {phase_name}
```

**Output** (TOON):
```toon
status: success
phase: 3-outline
skill: solution-outline
description: Create solution outline with deliverables
```

### get-routing-context

Get combined routing context (phase + skill + progress in one call).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get-routing-context \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
title: Add caching layer
current_phase: 3-outline
skill: solution-outline
skill_description: Create solution outline with deliverables
total_phases: 6
completed_phases: 2
```

### self-test

Verify manage-status health (checks imports, phase routing table, directory access).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status self-test
```

**Output** (TOON):
```toon
status: success
passed: 4
failed: 0
```

---

## Valid Phases & Routing

Phase set, transition rules, and phase-to-skill routing are defined in [standards/status-lifecycle.md](standards/status-lifecycle.md). The standard 6-phase model (`1-init` through `6-finalize`) is sequential — the `transition` command enforces ordering.

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
| `mark-step-done` | `--plan-id --phase --step --outcome [--display-detail] [--force]` | Record phase step outcome (+ optional display detail) in `metadata.phase_steps` |
| `get-context` | `--plan-id` | Get combined status context |
| `list` | `[--filter PHASE]` | Discover all plans, optionally filtered by phase |
| `transition` | `--plan-id --completed` | Mark phase done, advance to next |
| `archive` | `--plan-id [--dry-run]` | Archive completed plan |
| `delete-plan` | `--plan-id` | Delete entire plan directory |
| `route` | `--phase` | Get skill name for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |
| `self-test` | _(none)_ | Verify manage-status health |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Exit Code | Cause |
|------------|-----------|-------|
| `invalid_plan_id` | 1 | Plan ID not in kebab-case format |
| `file_not_found` | 1 | status.json doesn't exist |
| `file_exists` | 1 | status.json already exists (use `--force`) |
| `invalid_phase` | 1 | Phase name not in the phases list (set-phase, update-phase, transition) |
| `phase_not_found` | 1 | Phase doesn't exist in this plan's status.json phases array |
| `unknown_phase` | 1 | Phase name not in the static valid phases set (`1-init` through `6-finalize`); only used by `route` command |
| `plan_not_found` | 1 | Plan directory does not exist (delete-plan command) |
| `not_found` | 1 | Plan directory not found (archive command) |
| `not_found` | 0 | Metadata field doesn't exist — valid query result (returns `value: null`), not an error |
| `conflict` | 1 | `mark-step-done`: step already has a different outcome and `--force` was not supplied |
| `legacy_string_entry` | 1 | `mark-step-done`: existing entry uses the pre-migration bare-string shape; caller must migrate to dict shape before retrying |
| `invalid_outcome` | 1 | `mark-step-done`: outcome not in `done`/`skipped` |
| `invalid_argument` | 1 | `mark-step-done`: empty `--phase` or `--step` |

---

## Integration

**Called by**: `plan-marshall:plan-marshall` orchestrator for phase transitions, `phase-1-init` for initial status creation, and `phase-6-finalize` for archiving.

### With phase skills

Phase skills read/update status through manage-status:
- phase-1-init: Creates status with `create`
- phase-2-refine onwards: Uses `set-phase`, `metadata`, `get-context`, `transition`
- phase-6-finalize: Uses `archive` for completed plans

### With agents

Agents use `metadata` to store change_type and other classification data.

## Related

- `plan-marshall` — Orchestrator that drives phase transitions
- `phase-1-init` through `phase-6-finalize` — Phase-specific skills routed to by manage-status
- `manage-metrics` — Augments phase tracking with timing and token data
- `manage-config` — System configuration consumed by status operations
