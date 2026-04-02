---
name: manage-lifecycle
description: Plan lifecycle operations - discovery, phase transitions, archiving, and routing
user-invocable: false
scope: plan
---

# Manage Lifecycle Skill

Plan lifecycle operations including discovery, phase transitions, archiving, and routing context.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify .plan/ files directly; all mutations go through the script API
- Do not invent script arguments not listed in the Script API table
- Do not skip phase transition validation

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle {command} {args}`
- Phase transitions must use the `transition` command (never manual file edits)
- Routing context is read-only; use `get-routing-context` for combined state

## Valid Phases

The standard phase set (must be used in order):

`1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`

Phase transitions are sequential — you cannot skip phases. The `transition` command enforces this ordering.

## Script API

Script: `plan-marshall:manage-lifecycle:manage-lifecycle`

| Command | Parameters | Description |
|---------|------------|-------------|
| `list` | `[--filter PHASE]` | Discover all plans, optionally filtered by current phase name |
| `transition` | `--plan-id --completed` | Mark `--completed` phase as done, advance to next phase. Validates phase ordering. |
| `archive` | `--plan-id [--dry-run]` | Archive completed plan (moves to `.plan/archived-plans/YYYY-MM-DD-{plan_id}`). Plan must be in final phase with status `done`. |
| `route` | `--phase` | Get skill name for phase (format: `N-name`, e.g., `3-outline`) |
| `get-routing-context` | `--plan-id` | Get combined routing context (phase + skill + progress in one call, avoids multiple separate queries) |
| `self-test` | _(none)_ | Verify manage-lifecycle health (checks phase routing table, status operations, archive paths — 5 internal checks) |

## TOON Output Examples

**List response**:
```toon
status: success
total: 2

plans[2]{id,current_phase,status}:
my-feature,3-outline,in_progress
bugfix-123,5-execute,in_progress
```

**Transition response**:
```toon
status: success
plan_id: my-feature
completed_phase: 3-outline
next_phase: 4-plan
```

**Archive response**:
```toon
status: success
plan_id: my-feature
archived_to: .plan/archived-plans/2026-04-02-my-feature
```

**Route response**:
```toon
status: success
phase: 3-outline
skill: solution-outline
description: Create solution outline with deliverables
```

**Get-routing-context response**:
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

**Self-test response**:
```toon
status: success
passed: 5
failed: 0
```

## Error Responses

All errors return TOON with `status: error` and exit code 1.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `file_not_found` | status.json doesn't exist for plan |
| `unknown_phase` | Phase name not in valid phases set |
| `invalid_transition` | Attempting to skip phases or complete out of order |
| `not_archivable` | Plan not in final phase or final phase not done |
| `no_plans_found` | No plan directories exist in `.plan/plans/` |

```toon
status: error
plan_id: my-feature
error: invalid_transition
message: Cannot complete 3-outline before 2-refine is done
```

## Phase-to-Skill Routing

The `route` command maps phases to their implementation skills:

| Phase | Skill |
|-------|-------|
| `1-init` | `plan-marshall:phase-1-init` |
| `2-refine` | `plan-marshall:phase-2-refine` |
| `3-outline` | `plan-marshall:phase-3-outline` |
| `4-plan` | `plan-marshall:phase-4-plan` |
| `5-execute` | `plan-marshall:phase-5-execute` |
| `6-finalize` | `plan-marshall:phase-6-finalize` |

## Related Skills

- `manage-status` — Underlying status.json operations (lifecycle delegates to this for storage)
- `plan-marshall` — Orchestrator that drives phase transitions
- `phase-1-init` through `phase-6-finalize` — Phase-specific skills routed to by lifecycle
