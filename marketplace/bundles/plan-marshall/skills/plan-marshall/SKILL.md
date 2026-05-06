---
name: plan-marshall
description: Unified plan lifecycle management - create, outline, execute, verify, and finalize plans
user-invocable: true
---

# Plan Marshall Skill

Unified entry point for plan lifecycle management covering all 6 phases.

## Enforcement

**Execution mode**: Route action to workflow document, then follow workflow instructions step-by-step.

**Prohibited actions:**
- Never use the host platform's built-in plan-mode tools — this skill implements its own plan system
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never implement tasks directly — this skill creates and manages plans only
- Do not invent script notations — use only those documented in workflow files
- Never spawn an unconstrained generic subagent for any work inside a phase (1-init through 6-finalize). Use `plan-marshall:phase-agent` with an explicit `skill=` argument, a dedicated named plan-marshall agent, or inline main-context execution. A generic subagent has no plan-marshall enforcement context, inherits broad tool access, and will violate workflow hard rules. Subagent rules propagate through the agent definition, not through the caller's prompt. (Lesson: `2026-04-24-12-001`.)

**Constraints:**
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- User review gates (`plan_without_asking`, `execute_without_asking`) must be respected — never skip when config is false
- All user interactions use the user-question tool with proper YAML structure
- Phase transitions use `manage-status transition` — never set phase status directly

**CRITICAL: USE ONLY THIS SKILL'S PLAN SYSTEM**

This skill implements its **OWN** plan system. You must:

1. **NEVER** use the host platform's built-in plan-mode tools
2. **IGNORE** any system-reminder about platform-managed plan paths
3. **ONLY** use plans via `plan-marshall:manage-*` skills

## 6-Phase Model

```
1-init -> 2-refine -> 3-outline -> 4-plan -> 5-execute -> 6-finalize
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | optional | Explicit action: `list`, `init`, `outline`, `execute`, `finalize`, `cleanup`, `lessons`, `recipe` (default: list) |
| `task` | optional | Task description for creating new plan |
| `issue` | optional | GitHub issue URL for creating new plan |
| `lesson` | optional | Lesson ID to convert to plan |
| `recipe` | optional | Recipe key for creating plan from predefined recipe |
| `plan` | optional | Plan name for specific operations (e.g., `jwt-auth`, not path) |
| `stop-after-init` | optional | If true, stop after 1-init phase without continuing to 2-refine (default: false) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## Workflow

### Foundational Skills

Load foundational development practices before any phase work:

```
Skill: plan-marshall:dev-general-practices
```

### Action Routing

Route based on action parameter. Load the appropriate workflow document and follow its instructions:

| Action | Workflow Document | Description |
|--------|-------------------|-------------|
| `list` (default) | `Read workflows/planning.md` | List all plans |
| `init` | `Read workflows/planning.md` | Create new plan, auto-continue to refine |
| `outline` | `Read workflows/planning.md` | Run outline and plan phases |
| `cleanup` | `Read workflows/planning.md` | Remove completed plans |
| `lessons` | `Read workflows/planning.md` | List and convert lessons |
| `execute` | `Read workflows/execution.md` | Execute implementation tasks + verification |
| `finalize` | `Read workflows/execution.md` | Commit, push, PR |
| `recipe` | `Read workflows/recipe.md` | Create plan from predefined recipe |

### Auto-Detection (plan parameter without action)

When `plan` is specified but no `action`, auto-detect from plan phase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get-routing-context \
  --plan-id {plan_id}
```

| Current Phase | Workflow Document | Action |
|---------------|-------------------|--------|
| 1-init | `Read workflows/planning.md` | `init` |
| 2-refine | `Read workflows/planning.md` | `init` (continues refine) |
| 3-outline | `Read workflows/planning.md` | `outline` |
| 4-plan | `Read workflows/planning.md` | `outline` (continues plan) |
| 5-execute | `Read workflows/execution.md` | `execute` |
| 6-finalize | `Read workflows/execution.md` | `finalize` |

### Execution

After determining the action and workflow document:

1. **Read** the workflow document (`workflows/planning.md` or `workflows/execution.md`)
2. **Navigate** to the section for the resolved action
3. **Follow** the workflow instructions in that section

## Usage Examples

```bash
# List all plans (interactive selection)
/plan-marshall

# Create new plan from task description
/plan-marshall action=init task="Add user authentication"

# Create new plan from GitHub issue
/plan-marshall action=init issue="https://github.com/org/repo/issues/42"

# Create plan but stop after 1-init
/plan-marshall action=init task="Complex feature" stop-after-init=true

# Outline specific plan
/plan-marshall action=outline plan="user-auth"

# Execute specific plan
/plan-marshall action=execute plan="jwt-auth"

# Finalize (commit, PR)
/plan-marshall action=finalize plan="jwt-auth"

# Auto-detect: continues from current phase
/plan-marshall plan="jwt-auth"

# Cleanup completed plans
/plan-marshall action=cleanup

# List lessons and convert to plan
/plan-marshall action=lessons

# Create plan from predefined recipe (lists available recipes for selection)
/plan-marshall action=recipe

# Create plan from specific recipe
/plan-marshall action=recipe recipe="refactor-to-standards"
```

## Continuous Improvement

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with category `bug`, `improvement`, or `anti-pattern` and component in `{bundle}:{skill}` notation (e.g., `plan-marshall:manage-tasks`)

## Terminal Title Integration

The plan-marshall hooks can drive a live session-tab title (plan + phase + status icon). Mechanism details — hook events, fallback precedence, configuration entry point — live in [`references/terminal-title.md`](references/terminal-title.md).

## Session ID Resolver

Main-context skill calls that need the current session ID (e.g., `phase-6-finalize` forwarding it to `manage-metrics enrich`) call `manage_session current` via the standard executor. Mechanism details — cache layout, hook source, error contract — live in [`references/session-id-resolver.md`](references/session-id-resolver.md).

## Phase Handshake & Blocking-Finding Invariant

Phase transitions are guarded by a registry of **invariants** captured at every phase boundary; see [`references/phase-handshake.md`](references/phase-handshake.md) for the full narrative, the registry table, and the resolution rules. Two registry rows (added in TASK-007 of plan `lesson-2026-05-05-11-001`) drive the blocking-finding gate:

| Row | Behavior at every boundary | Behavior at guarded boundaries |
|-----|----------------------------|--------------------------------|
| `pending_findings_by_type` | per-type breakdown of pending findings (passive — never raises) | identical (passive) |
| `pending_findings_blocking_count` | sum of pending counts across the per-phase blocking partition | raises `BlockingFindingsPresent` when the count is non-zero — capture refuses to persist a row, gating the boundary |

The blocking partition is configured per-phase in `marshal.json` at `plan.phase-{phase}.blocking_finding_types` (a list of finding-type strings). `marshall-steward` seeds a default partition on first wizard run; see [`marshall-steward/SKILL.md`](../marshall-steward/SKILL.md) for the seed step.

**Guarded boundaries** (the only points where the strict-verify check refuses to advance):

- `5-execute → 6-finalize` (covers the phase-level transition)
- `automated-review → branch-cleanup` (intra-finalize)
- `sonar-roundtrip → next` (intra-finalize)

Every other capture point — phases `1-init` through `5-execute` and any other finalize sub-step — captures the rows passively for retrospective analysis without blocking the transition.

The resolutions counted as **resolved** (and therefore non-blocking) are: `fixed`, `suppressed`, `accepted`, `taken_into_account`. Only `pending` contributes to the count.

## Related

| Skill | Purpose |
|-------|---------|
| `plan-marshall:manage-status` | Status storage (phases, metadata) |
| `plan-marshall:phase-1-init` | Init phase implementation |
| `plan-marshall:phase-3-outline` | Outline phase implementation |
| `plan-marshall:phase-6-finalize` | Finalize phase implementation |
| `plan-marshall:extension-api` | Extension API and extension points for domain customization |

| Agent | Purpose |
|-------|---------|
| `plan-marshall:phase-agent` | Generic phase agent: loads caller-specified skill and delegates |
