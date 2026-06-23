---
name: manage-status
description: Manage status.json files with phase tracking, metadata, and lifecycle operations
user-invocable: false
mode: script-executor
scope: plan
---

# Manage Status Skill

Manage status.json files with phase tracking, metadata, and lifecycle operations. Handles plan status storage (JSON), phase operations, metadata management, plan discovery, phase transitions, archiving, and routing.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid phase status values: `pending`, `in_progress`, `done`
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
  "title_token": "lock-owned",
  "phases": [
    {"name": "1-init", "status": "in_progress"},
    {"name": "2-refine", "status": "pending"},
    {"name": "3-outline", "status": "pending"},
    {"name": "4-plan", "status": "pending"},
    {"name": "5-execute", "status": "pending"},
    {"name": "6-finalize", "status": "pending"}
  ],
  "metadata": {
    "change_type": "feature",
    "use_worktree": true,
    "worktree_path": "/abs/path/.plan/local/worktrees/my-feature",
    "worktree_branch": "feature/my-feature"
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
| `title_token` | string (optional) | Transient title-token state marker. Values: `lock-waiting`, `lock-owned`. Written by `title-token set`; cleared by `title-token clear`. Absent when no token is active. Consumed by the `manage-terminal-title` composer for glyph selection; not a persisted plan field — it is ephemeral session state. |
| `phases` | list | Phase objects with name and status |
| `metadata` | table | Key-value metadata (common fields: `change_type`, `confidence`, `domain`, `use_worktree`, `worktree_path`, `worktree_branch`) |
| `created` | string | ISO timestamp of creation |
| `updated` | string | ISO timestamp of last update |

### Phase Status Values

| Status | Description |
|--------|-------------|
| `pending` | Phase not yet started |
| `in_progress` | Phase currently active |
| `done` | Phase completed |

### Worktree Metadata Convention

`status.metadata` is the canonical source of truth for whether a plan
runs in an isolated git worktree. `create` seeds only `use_worktree`;
`worktree_branch` and `worktree_path` are persisted at phase-5
materialization, and `get-worktree-path` reads all three:

| Field | Type | When set | Description |
|-------|------|----------|-------------|
| `use_worktree` | bool | Always (seeded by `create`) | `true` when the plan runs in an isolated worktree, `false` when it runs against the main checkout. Never absent on plans created via `create`. |
| `worktree_path` | string | Persisted at phase-5-execute Step 2.5 (absent until then) | Absolute path to the worktree root. Used by `get-worktree-path`, build wrappers (`--plan-id` resolution), and phase-entry assertions. Phases 1-4 record no path; phase-5-execute Step 2.5 persists the resolved path once `git worktree add` runs. |
| `worktree_branch` | string | Persisted at phase-5-execute Step 2.5 (absent until then) | Feature branch ref (`feature/{plan_id}`) derived and checked out at materialization. Recorded for the audit trail and consumed by `workflow-integration-git` worktree subcommands. |

Downstream consumers MUST read these fields via `get-worktree-path`
rather than re-deriving the path from filesystem layout. Re-derivation
breaks if the platform-neutral worktree root constant ever changes
again, and it duplicates logic that `manage-status` already owns.

---

## Operations

Script: `plan-marshall:manage-status:manage-status`

### create

Create status.json with initial phases. Optionally records the
worktree intent (`use_worktree`) into `status.metadata`; the branch and
the resolved `worktree_path` are derived and persisted later, at phase-5
materialization.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title {title} \
  --phases {comma-separated-phases} \
  [--force] \
  [--use-worktree]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--title` (required): Plan title
- `--phases` (required): Comma-separated phase names in execution order (e.g., `1-init,2-refine,3-outline,4-plan,5-execute,6-finalize`). Order matters — it determines progress calculation and transition sequence.
- `--force`: Overwrite existing status.json
- `--use-worktree` (optional): Mark the plan as running in an isolated git worktree. Seeds only `status.metadata.use_worktree=true`; the feature branch (`feature/{plan_id}`) and the resolved `worktree_path` are derived and persisted later by phase-5-execute Step 2.5 once `git worktree add` runs. When `--use-worktree` is omitted, `status.metadata.use_worktree=false` is seeded explicitly so downstream resolvers never have to treat absence-of-metadata as "main-checkout".

**Output — main-checkout** (TOON):
```toon
status: success
plan_id: my-feature
file: status.json
created: true
plan:
  title: My Feature
  current_phase: 1-init
use_worktree: false
```

**Output — worktree (intent recorded)** (TOON):
```toon
status: success
plan_id: my-feature
file: status.json
created: true
plan:
  title: My Feature
  current_phase: 1-init
use_worktree: true
```

The branch and `worktree_path` are absent here — phase-5-execute Step 2.5 derives `feature/{plan_id}` and persists both at materialization.

### read

Read entire status.json content.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-phase \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status progress \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field {field_name} \
  --value {value}
```

**Get metadata**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
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

Record the outcome of a phase step inside `status.metadata.phase_steps`. Phase skills use this to persist intra-phase progress (e.g., discovery, drift-detection) so that resuming a phase can skip completed steps. Outcomes are `done`, `skipped`, `loop_back`, or `failed`. An optional `--display-detail` one-line string is persisted alongside the outcome so downstream renderers (phase-6-finalize vertical-steps block, etc.) can surface user-facing step summaries. Loop-back outcomes carry a mandatory `--loop-back-target` granularity classifier (see "Loop-back target classification" below).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --step {step_id} \
  --outcome {done|skipped|loop_back|failed} \
  [--display-detail "one-line user-facing detail"] \
  [--head-at-completion <sha>] \
  [--loop-back-target {5-execute|6-finalize}] \
  [--force]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase` (required): Phase name (e.g., `5-execute`)
- `--step` (required): Step identifier within the phase (free-form string chosen by the phase skill)
- `--outcome` (required): `done`, `skipped`, `loop_back`, or `failed`
- `--display-detail` (optional at CLI level, required-by-convention for phase-6-finalize steps per the phase-6-finalize interface contract): One-line user-facing detail string. Persisted as `null` when omitted.
- `--head-at-completion` (optional): Git SHA captured at step completion. Persisted alongside outcome and consulted by resumable phase dispatchers (e.g., phase-6-finalize `pre-push-quality-gate`) to detect HEAD advancement.
- `--loop-back-target` (REQUIRED when `--outcome=loop_back`, FORBIDDEN otherwise): Loop-back target phase. Must be one of `5-execute` (full phase rollback for fix-task-required dispositions) or `6-finalize` (inline replay for inline-fixable dispositions). See "Loop-back target classification" below.
- `--force` (optional): Overwrite an existing differing outcome

**Loop-back target classification**:

The `--loop-back-target` flag encodes the granularity invariant from the phase-6-finalize "Loop-back Target Contract" section. Two legal values:

- `5-execute` — full phase rollback for **fix-task-required** dispositions. Use when triage allocated one or more fix tasks (`fix_tasks_created > 0`) or deferred any findings to overflow (`overflow_deferred > 0`). The continuation hook re-dispatches `phase-5-execute` against the freshly-allocated fix tasks before re-entering the finalize FOR loop.
- `6-finalize` — inline replay for **inline-fixable** dispositions. Use when triage resolved every finding via SUPPRESS, narrow-rationale ACCEPT, or single-annotation FIX (no fix-task allocation, no overflow). The continuation hook stays in `6-finalize`, does NOT call `set-phase`, and re-fires the loop-back-marked step from the resumable re-entry check.

The flag is REQUIRED on every `loop_back` outcome (returns `error: missing_loop_back_target` when absent) and FORBIDDEN on every other outcome (returns `error: unexpected_loop_back_target`). The `argparse` `choices` enforce the two-value enumeration at parse time. There is no backwards-compat fallback — every loop-back-emitting call site MUST classify the disposition before persisting the outcome.

**Storage shape** (breaking — replaces the old bare-string shape):

```json
status.metadata.phase_steps[{phase}][{step}] = {
  "outcome": "done" | "skipped" | "loop_back" | "failed",
  "display_detail": <string> | null,
  "head_at_completion": <sha> | absent,
  "loop_back_target": "5-execute" | "6-finalize" | absent
}
```

Both the `metadata` and `phase_steps` containers are created on demand. Bare-string entries from prior versions are treated as drift — see conflict semantics below. The `head_at_completion` and `loop_back_target` keys are only present when the corresponding flag was supplied (per the `_build_entry` helper); `loop_back_target` is structurally guaranteed to be present iff `outcome == "loop_back"`.

**Semantics**:
- **Idempotent on identical outcome AND display_detail AND head_at_completion AND loop_back_target**: If the step already has the requested outcome and all four fields match, no file write occurs and `changed: false` is returned.
- **Detail / head / loop_back_target update**: If the outcome matches but any of `display_detail`, `head_at_completion`, or `loop_back_target` differ, the command updates the entry in place and returns `changed: true`.
- **Conflict on differing outcome**: If the step already has a different outcome and `--force` is not supplied, the command returns `error: conflict` with the existing outcome surfaced in the response. Supplying `--force` overwrites the existing value (and detail / head / loop_back_target).
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

### assert-step-recorded

Read-only verdict over `status.metadata.phase_steps[{phase}][{step}]`: does a terminal step record exist? The phase-6-finalize dispatcher calls this after every dispatched (Task-agent) step returns, to detect the silent gap where a step returns `status: success` but skips its mandated `mark-step-done` side-effect — the omission that otherwise stays invisible until the `phase_steps_complete` handshake deadlocks the phase transition with no per-step attribution. The verb performs **zero writes** to `status.json`.

A record counts as *recorded* iff a dict entry with a terminal `outcome` in `{done, skipped, loop_back, failed}` is present (a `loop_back` record counts as terminal for guard purposes — the dispatcher re-fires it via the resumable re-entry check). Bare-string legacy entries and missing entries both report `recorded: false`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status assert-step-recorded \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --step {step_id} \
  [--require-terminal]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase` (required): Phase name (e.g., `6-finalize`)
- `--step` (required): Step identifier within the phase
- `--require-terminal` (optional): Escalate a missing terminal record to a `status: error` verdict instead of returning `recorded: false`. Two error branches are distinguished: `step_record_mismatched_key` when the queried step has no record BUT a terminal record exists under a different (near-miss) key in the same phase — the dispatched step recorded under the wrong key; `step_record_missing` when no terminal record exists under any key in the phase. The post-dispatch guard passes this flag so a missing record is a branchable failure verdict rather than a soft boolean.

**Output — recorded** (TOON):
```toon
status: success
plan_id: my-feature
phase: 6-finalize
step: ci-verify
recorded: true
outcome: done
```

**Output — not recorded (no `--require-terminal`)** (TOON):
```toon
status: success
plan_id: my-feature
phase: 6-finalize
step: ci-verify
recorded: false
outcome: null
```

**Output — missing record under `--require-terminal`** (TOON):
```toon
status: error
plan_id: my-feature
error: step_record_missing
phase: 6-finalize
step: ci-verify
recorded: false
outcome: null
message: No terminal record for step 'ci-verify' in phase '6-finalize': the dispatched step returned without recording a mark-step-done outcome (expected one of ['done', 'skipped', 'loop_back', 'failed']).
```

**Output — mismatched key under `--require-terminal`** (TOON): the queried step has no record, but a terminal record exists under a near-miss key in the same phase.
```toon
status: error
plan_id: my-feature
error: step_record_mismatched_key
phase: 6-finalize
step: plan-marshall:plan-retrospective
recorded: false
outcome: null
orphan_key: plan-retrospective
orphan_outcome: done
message: No terminal record for step 'plan-marshall:plan-retrospective' in phase '6-finalize', but a terminal record exists under the near-miss key 'plan-retrospective' (outcome 'done'). The dispatched step recorded its mark-step-done outcome under the wrong key — expected the queried step name 'plan-marshall:plan-retrospective'.
```

### get-context

Get combined status context (phase, progress, metadata) in one call.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-context \
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

### get-worktree-path

Resolve the persisted worktree path for a plan from `status.metadata`.
Allows callers (build wrappers, `git-workflow`, phase-entry assertions)
to look up the active worktree by `--plan-id` alone — without
re-deriving the path from filesystem layout, and without taking a
`--project-dir` argument.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

**Parameters**:
- `--plan-id` (required): Plan identifier

**Behavior** (tri-state, discriminated by `worktree_state`):
- When `metadata.use_worktree == false` (or metadata is absent) → `worktree_state: disabled`, `worktree_path: ''`. Callers interpret this as "plan runs against the main checkout".
- When `metadata.use_worktree == true` and `metadata.worktree_path` is set → `worktree_state: materialized`, `worktree_path: <abs>`. The worktree directory has been created.
- When `metadata.use_worktree == true` and `metadata.worktree_path` is missing/empty → `worktree_state: pending`, `worktree_path: ''`, `not_yet_materialized: true`. The plan opted into worktree mode but the directory has not been materialized yet (pre-materialization). Callers MUST fall back to the main checkout cwd.

The `worktree_unresolved` error path is owned by `phase_handshake verify`, which validates filesystem-resolvability of a non-empty `worktree_path`. This subcommand never returns that error; it returns `pending` for the pre-materialization state instead.

**Output — disabled (main checkout)** (TOON):
```toon
status: success
plan_id: my-feature
use_worktree: false
worktree_state: disabled
worktree_path: ""
```

**Output — materialized** (TOON):
```toon
status: success
plan_id: my-feature
use_worktree: true
worktree_state: materialized
worktree_path: /abs/path/.plan/local/worktrees/my-feature
worktree_branch: feature/my-feature
```

**Output — pending (pre-materialization)** (TOON):
```toon
status: success
plan_id: my-feature
use_worktree: true
worktree_state: pending
worktree_path: ""
not_yet_materialized: true
```

### list

Discover all plans, optionally filtered by current phase.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list \
  [--filter PHASE]
```

**Parameters**:
- `--filter` (optional): Comma-separated phase names to filter by

**Output** (TOON):
```toon
status: success
total: 2

plans[2]{id,current_phase,status,location}:
my-feature,3-outline,in_progress,current
bugfix-123,5-execute,in_progress,worktree
```

Each entry carries a `location` field: `current` (the plan directory lives on the cwd checkout) or `worktree` (the plan directory was moved into its worktree at phase-5 entry, ADR-002). The merged list is deduped by plan id (a moved-in plan appears exactly once) and sorted by id.

**Concurrent-session visibility**: per [ADR-002](../../../../../doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc), a plan's non-git-controlled runtime state (its plan directory) MOVES into the plan's own worktree at phase-5 entry and moves back to main at finalize. While a plan is executing (phase-5+), its plan directory therefore lives in its worktree, not on main. `cmd_list` discovers both sources: it enumerates the main checkout's plans (`location: current`) AND scans `get_worktree_root()`'s child worktrees for moved-in plans (`location: worktree`), so a `list` run from the main checkout DOES surface a plan that is mid-flight in its worktree — the ADR-002 move-in is exactly why the worktree scan is necessary. See `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md` for the worktree lifecycle that produces this property.

### transition

Mark a phase as done and advance to next phase. Validates phase ordering.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status archive \
  --plan-id {plan_id} \
  [--dry-run] \
  [--reason REASON]
```

`--reason REASON` persists a human-readable explanation to
`status.metadata.archived_reason` on the archived plan. The field is additive
(omitted when the flag is absent — no schema migration). Used by `plan-doctor`
rule `stuck-low-confidence-archive` as the canonical remediation flag so a
retrospective audit can distinguish intentional abandonment from neglect.
Example values: `low_confidence`, `scope_changed`, `superseded_by_<plan_id>`.

**Output** (TOON):
```toon
status: success
plan_id: my-feature
archived_to: .plan/archived-plans/2026-04-02-my-feature
```

### delete-plan

Delete an entire plan directory. Used when user selects "Replace" for an existing plan during plan-init.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status route \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-routing-context \
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

### planning-lane

Deterministic planning-lane router with two sub-verbs (`route` / `escalate`). Resolves `planning_lane ∈ {light, deep}` from cheap field reads plus a `request.md` regex — **zero codebase discovery, zero LLM cognition**. The default is `light`; any deep-precondition signal forces `deep`. Escalation is **one-way** (light may ratchet to deep, never deep→light).

**route** — evaluate the signal set, resolve the lane, and (with `--persist`) write `status.metadata.planning_lane`. Emits one decision-log line naming every signal value and the winning predicate.

The signal set (`deep` IFF any deep-precondition fires; otherwise `light`):

| # | Signal | Source (cheap read) | → deep when |
|---|--------|---------------------|-------------|
| S1 | `plan_source` | `status.metadata.plan_source` | source is free-form (absent/unset) **AND** S5 concreteness fails (`lesson`/`recipe` bias light) |
| S2 | `scope_estimate` | `references.scope_estimate` | ∈ {`multi_module`, `broad`, `none`, unset} (`surgical`/`single_module` → light) |
| S3 | `change_type` | `status.metadata.change_type` | ∈ {`feature`, `feature_breaking`} (`bug_fix`/`tech_debt`/`enhancement`/`verification` → light) |
| S4 | `compatibility` | `marshal.json plan.phase-2-refine.compatibility` | == `breaking` |
| S5 | request concreteness | regex over `request.md` clarified/original body | body names NO file path **AND** NO concrete fix signal (fenced code block / `python3 .plan/execute-script.py` CLI / `manage-*` notation) |
| S6 | explicit override | `status.metadata.planning_lane_override` (or `--lane-override deep`) | == `deep` forces deep (one-way) |

**deep-lane short-circuit** — `plan.phase-1-init.deep_lane` is read BEFORE the signal set: `always` → force `deep`; `never` → force `light` (the DQ3 hard-escalation ratchet still fires unless `plan.phase-1-init.escalation: never` is also set); `auto` (default) → the signal set decides.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane route \
  --plan-id {plan_id} [--lane-override deep|light] [--persist]
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
planning_lane: deep
ceremony_deep_lane: auto
decision_predicate: signal_set
fired_signals[2]:
  - "S3:change_type"
  - "S4:compatibility"
persisted: true
classification_validation:
  mismatch_count: 0
  mismatches[0]:
  findings_emitted: 0
```

`route` runs the deterministic **classification-validation gate** (see `classification-validate` below) as a pre-route pass and surfaces its result under `classification_validation`. The gate is **flag-not-block** — it never changes the resolved lane; a flagged mismatch only records a Q-Gate finding.

**escalate** — the one-way light→deep ratchet evaluated inside the light-lane envelope. Sets `planning_lane=deep`, `lane_escalated=true`, and records the `escalation_trigger` (`explosion` / `premise` / `cross_cutting`). The `lane_escalated` flag is sticky — a deep lane never reverts, so there is no downgrade verb.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane escalate \
  --plan-id {plan_id} --trigger explosion|premise|cross_cutting [--persist]
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
planning_lane: deep
lane_escalated: true
escalation_trigger: explosion
persisted: true
```

### classification-validate

Deterministic **classification-validation gate** — cross-checks the plan's `change_type` and `scope_estimate` against cheap request signals and emits a phase-1-init Q-Gate finding on a mismatch. **Zero codebase discovery, zero LLM cognition; flag-not-block** — it NEVER gates routing. The gate runs automatically as a pre-route pass inside `planning-lane route`; this subcommand exposes it standalone (e.g., for a phase-1-init invocation that does not route immediately).

Two mismatch classes are flagged, both chosen to raise zero false positives:

- **`feature_as_bug_fix`** — `change_type == bug_fix` while the deterministic change-type heuristic (the same scoring engine `change-type-heuristic` uses) resolves a **non-ambiguous** `feature` winner from the request narrative. A borderline / tied narrative never trips it.
- **`non_empty_affected_files_with_null_scope`** — `references.affected_files` is non-empty while `references.scope_estimate` is null / empty / `none`. Deterministic data-gap check, no heuristic.

Each flagged mismatch records a `warning`-severity `anti-pattern` Q-Gate finding against the `2-refine` phase (the Q-Gate store opens at `2-refine`; `1-init` is not a Q-Gate phase, and `2-refine` is exactly where classification is revisited) and emits one `decision.log` line. Findings dedup by title, so re-running the gate does not duplicate them.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status classification-validate \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
change_type: bug_fix
scope_estimate: null
mismatch_count: 1
mismatches[1]{mismatch,title,finding_status,hash_id}:
  feature_as_bug_fix,Classification mismatch: change_type=bug_fix over a feature-shaped request,success,a1b2c3d4
findings_emitted: 1
blocked: false
```

`blocked` is always `false` — the gate is advisory. When no mismatch fires, `mismatch_count: 0` and `findings_emitted: 0`.

### self-test

Verify manage-status health (checks imports, phase routing table, directory access).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status self-test
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

**Script**: `plan-marshall:manage-status:manage-status`

| Command | Parameters | Description |
|---------|------------|-------------|
| `create` | `--plan-id --title --phases [--force] [--use-worktree]` | Create status.json (records `use_worktree` intent when `--use-worktree` is present; the branch and `worktree_path` are derived at phase-5-execute Step 2.5) |
| `read` | `--plan-id` | Read full status |
| `set-phase` | `--plan-id --phase` | Set current phase (marks as in_progress) |
| `update-phase` | `--plan-id --phase --status` | Update specific phase status |
| `progress` | `--plan-id` | Calculate progress percentage |
| `metadata` | `--plan-id --get/--set --field [--value]` | Get/set metadata fields |
| `title-token set` | `--plan-id --state {lock-waiting\|lock-owned}` | Write the field-only `status.title_token` state marker. No rendering — `manage-terminal-title` owns title composition + glyph vocabulary. |
| `title-token clear` | `--plan-id` | Remove the `status.title_token` field (idempotent — no-op when already absent). |
| `mark-step-done` | `--plan-id --phase --step --outcome [--display-detail] [--head-at-completion] [--loop-back-target] [--force]` | Record phase step outcome (+ optional display detail / HEAD SHA / loop-back target) in `metadata.phase_steps` |
| `assert-step-recorded` | `--plan-id --phase --step [--require-terminal]` | Read-only verdict: reports `recorded: true` iff a terminal `metadata.phase_steps[phase][step]` outcome exists. The phase-6-finalize post-dispatch guard. With `--require-terminal`, a near-miss orphan record under a different key returns `error: step_record_mismatched_key` (carrying `orphan_key`); a truly-absent record returns `error: step_record_missing`. Zero writes. |
| `get-context` | `--plan-id` | Get combined status context |
| `get-worktree-path` | `--plan-id` | Resolve persisted worktree path (returns empty string when `use_worktree==false`) |
| `list` | `[--filter PHASE]` | Discover all plans across the main checkout and its worktrees (each entry tagged `location: current`/`worktree`), optionally filtered by phase |
| `transition` | `--plan-id --completed` | Mark phase done, advance to next |
| `archive` | `--plan-id [--dry-run] [--reason REASON]` | Archive completed plan; `--reason` persists to `status.metadata.archived_reason` (used by `plan-doctor stuck-low-confidence-archive` rule) |
| `delete-plan` | `--plan-id` | Delete entire plan directory |
| `route` | `--phase` | Get skill name for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |
| `change-type-heuristic` | `--plan-id [--persist]` | Deterministic change-type classifier for phase-3-outline Step 4. Reads the clarified-request narrative (falling back to original_input) and scores it against a fixed keyword table — returns one of `feature`, `bug_fix`, `tech_debt`, `enhancement`, `verification`, `analysis`, or `ambiguous=true` when no keyword fires / two change types tie / confidence < 0.7. With `--persist`, writes the resolved change_type to `status.metadata.change_type` (skipped in the ambiguous branch so the LLM `detect-change-type` workflow is the single writer there). |
| `aggregate-confidence` | `--plan-id [--scores-file PATH] [--correctness N] [--completeness N] [--consistency N] [--non-duplication N] [--ambiguity N] [--module-mapping N] [--persist]` | Weighted-math confidence aggregator for phase-2-refine Step 10. Computes the overall confidence from per-dimension scores (0..100) using the fixed weights `correctness 20% / completeness 20% / consistency 20% / non-duplication 10% / ambiguity 20% / module-mapping 10%`. Missing dimensions default to 0 and are recorded in `missing_dimensions`. Scores can be supplied via `--scores-file` (JSON object keyed by dimension) and / or individual CLI flags; flags take precedence on conflict. With `--persist`, the overall confidence is written to `status.metadata.confidence`. |
| `planning-lane route` | `--plan-id [--lane-override deep\|light] [--persist]` | Deterministic planning-lane router. Resolves `planning_lane ∈ {light, deep}` from the DQ1 signal set (S1–S6) plus a `request.md` regex with zero discovery; `plan.phase-1-init.deep_lane` (`always`/`never`/`auto`) short-circuits the signals. Default is light; any deep signal forces deep. With `--persist`, writes `status.metadata.planning_lane`. Emits one decision-log line naming every signal value and the winning predicate. |
| `planning-lane escalate` | `--plan-id --trigger explosion\|premise\|cross_cutting [--persist]` | One-way light→deep ratchet. Sets `planning_lane=deep` + `lane_escalated=true` + `escalation_trigger`; the flag is sticky and there is no downgrade path. With `--persist`, writes the mutation to `status.metadata`. |
| `classification-validate` | `--plan-id` | Deterministic classification-validation gate (flag-not-block). Cross-checks `change_type` / `scope_estimate` against cheap request signals; flags `feature_as_bug_fix` (bug_fix stamp over a non-ambiguous feature narrative) and `non_empty_affected_files_with_null_scope`, recording a `warning` `anti-pattern` Q-Gate finding against `2-refine` per mismatch. NEVER blocks routing; runs automatically as a pre-route pass inside `planning-lane route`. |
| `self-test` | _(none)_ | Verify manage-status health |

---

## Canonical invocations

The canonical argparse surface for `manage-status.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-status` Canonical invocations → `transition`") instead of
restating the command inline.

### create

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id PLAN_ID --title TEXT --phases CSV \
  [--force] \
  [--use-worktree]
```

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id PLAN_ID
```

### set-phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
  --plan-id PLAN_ID --phase PHASE
```

### update-phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-phase \
  --plan-id PLAN_ID --phase PHASE --status {pending|in_progress|done}
```

### progress

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status progress \
  --plan-id PLAN_ID
```

### metadata

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id PLAN_ID --field FIELD \
  (--get | --set --value VALUE)
```

### get-context

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-context \
  --plan-id PLAN_ID
```

### get-worktree-path

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id PLAN_ID
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list \
  [--filter PHASES_CSV]
```

### transition

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id PLAN_ID --completed PHASE
```

### archive

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status archive \
  --plan-id PLAN_ID [--dry-run] [--reason REASON]
```

### route

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status route \
  --phase PHASE
```

### get-routing-context

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-routing-context \
  --plan-id PLAN_ID
```

### delete-plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
  --plan-id PLAN_ID
```

### mark-step-done

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id PLAN_ID --phase PHASE --step STEP_ID \
  --outcome {done|skipped|loop_back|failed} \
  [--force] [--display-detail TEXT] [--head-at-completion SHA]
```

### assert-step-recorded

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status assert-step-recorded \
  --plan-id PLAN_ID --phase PHASE --step STEP_ID \
  [--require-terminal]
```

### change-type-heuristic

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status change-type-heuristic \
  --plan-id PLAN_ID [--persist]
```

### aggregate-confidence

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status aggregate-confidence \
  --plan-id PLAN_ID \
  [--scores-file PATH] \
  [--correctness N] [--completeness N] [--consistency N] \
  [--non-duplication N] [--ambiguity N] [--module-mapping N] \
  [--persist]
```

### planning-lane

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane route \
  --plan-id PLAN_ID
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane escalate \
  --plan-id PLAN_ID --trigger explosion
```

### classification-validate

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status classification-validate \
  --plan-id PLAN_ID
```

### self-test

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status self-test
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Exit Code | Cause |
|------------|-----------|-------|
| `invalid_plan_id` | 1 | Plan ID not in kebab-case format |
| `file_not_found` | 1 | status.json doesn't exist |
| `file_exists` | 1 | status.json already exists (use `--force`) |
| `invalid_phase` | 1 | Phase name not in the phases list (set-phase, update-phase, transition) |
| `invalid_title_token_state` | 1 | `title-token set`: `--state` value not in `lock-waiting`/`lock-owned`. (Argparse `choices` normally catches this at parse time; this error fires only when the validation is bypassed at the API layer.) |
| `phase_not_found` | 1 | Phase doesn't exist in this plan's status.json phases array |
| `unknown_phase` | 1 | Phase name not in the static valid phases set (`1-init` through `6-finalize`); only used by `route` command |
| `plan_not_found` | 1 | Plan directory does not exist (delete-plan command) |
| `not_found` | 1 | Plan directory not found (archive command) |
| `not_found` | 0 | Metadata field doesn't exist — valid query result (returns `value: null`), not an error |
| `conflict` | 1 | `mark-step-done`: step already has a different outcome and `--force` was not supplied |
| `legacy_string_entry` | 1 | `mark-step-done`: existing entry uses the pre-migration bare-string shape; caller must migrate to dict shape before retrying |
| `invalid_outcome` | 1 | `mark-step-done`: outcome not in `done`/`skipped`/`loop_back`/`failed` |
| `invalid_argument` | 1 | `mark-step-done`: empty `--phase` or `--step` |
| `missing_loop_back_target` | 1 | `mark-step-done`: `--outcome=loop_back` supplied without `--loop-back-target`. The flag is REQUIRED on every loop_back outcome (no backwards-compat fallback). |
| `invalid_loop_back_target` | 1 | `mark-step-done`: `--loop-back-target` value not in `5-execute`/`6-finalize`. (Argparse `choices` normally catches this at parse time; this error fires only when the validation is bypassed at the API layer.) |
| `unexpected_loop_back_target` | 1 | `mark-step-done`: `--loop-back-target` supplied alongside an outcome other than `loop_back`. The flag is FORBIDDEN on `done`/`skipped`/`failed` outcomes. |
| `step_record_missing` | 0 | `assert-step-recorded --require-terminal`: no terminal record exists under any key for the named phase (the dispatched step returned without recording a `mark-step-done` outcome). Exit code is 0 — the post-dispatch guard branches on the TOON `error` field, not the process exit code. |
| `step_record_mismatched_key` | 0 | `assert-step-recorded --require-terminal`: the queried step has no terminal record, but a near-miss orphan terminal record exists under a different key in the same phase (the dispatched step recorded under the wrong key — e.g. a bare skill name instead of its fully-qualified manifest `step_id`). Carries `orphan_key` and `orphan_outcome`. Exit code is 0 — the guard branches on the TOON `error` field. |
| `worktree_unresolved` | 1 | `phase_handshake verify`: `metadata.use_worktree==true` and `metadata.worktree_path` is non-empty but does not resolve on the filesystem. `get-worktree-path` does not emit this error — it returns `worktree_state: pending` for the pre-materialization state. |

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
