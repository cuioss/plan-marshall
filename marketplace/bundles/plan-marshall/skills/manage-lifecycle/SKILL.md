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

## Script API

Script: `plan-marshall:manage-lifecycle:manage-lifecycle`

| Command | Parameters | Description |
|---------|------------|-------------|
| `list` | `[--filter]` | Discover all plans |
| `transition` | `--plan-id --completed` | Transition to next phase |
| `archive` | `--plan-id [--dry-run]` | Archive completed plan |
| `route` | `--phase` | Get skill for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |
| `self-test` | _(none)_ | Verify manage-lifecycle health |

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

```toon
status: error
plan_id: my-feature
error: invalid_plan_id
message: Invalid plan_id format: my-feature!!
```

```toon
status: error
plan_id: my-feature
error: file_not_found
message: status.json not found
```

```toon
status: error
phase: unknown
error: unknown_phase
message: Unknown phase: unknown
```

## Related Skills

- `manage-status` — Underlying status.json operations (lifecycle delegates to this)
- `plan-marshall` — Orchestrator that drives phase transitions
- `phase-1-init` through `phase-6-finalize` — Phase-specific skills routed to by lifecycle
