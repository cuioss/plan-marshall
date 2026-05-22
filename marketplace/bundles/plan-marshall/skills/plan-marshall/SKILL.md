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
- Never spawn an unconstrained generic subagent (e.g. `Task: general-purpose`) for any work inside a phase (1-init through 6-finalize). Use `plan-marshall:execution-context-{level}` with a `workflow:` notation pointing at the workflow doc, or inline main-context execution. A generic subagent has no plan-marshall enforcement context, inherits broad tool access, and will violate workflow hard rules. Subagent rules propagate through the agent definition, not through the caller's prompt. (Lesson: `2026-04-24-12-001`.)

**Constraints:**
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- User review gates (`init_without_asking`, `plan_without_asking`, `execute_without_asking`) must be respected — never skip when config is false
- All user interactions use `AskUserQuestion` tool with proper YAML structure
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
| `action` | optional | Explicit action: `list`, `init`, `outline`, `execute`, `finalize`, `cleanup`, `lessons`, `lessons-aggregate`, `recipe`. When omitted, the action is inferred from other parameters — see [Action Resolution](#action-resolution). |
| `task` | optional | Task description for creating new plan. Implies `action=init` when no explicit action is given. |
| `issue` | optional | GitHub issue URL for creating new plan. Implies `action=init` when no explicit action is given. |
| `lesson` | optional | Lesson ID to convert to plan. Implies `action=lessons` when no explicit action is given. |
| `recipe` | optional | Recipe key for creating plan from predefined recipe. Implies `action=recipe` when no explicit action is given. |
| `plan` | optional | Plan name for specific operations (e.g., `jwt-auth`, not path). When supplied without an explicit action, the action is auto-detected from the plan's current phase. |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## Workflow

### Foundational Skills

Load foundational development practices before any phase work:

```
Skill: plan-marshall:dev-agent-behavior-rules
```

### Action Resolution

Resolve the effective action in the following order. The first matching rule wins; stop at the first match.

1. **Explicit `action=` parameter** — use it as-is. If the value is not in the action table below, return `status: error` with a remediation message naming the valid actions.
2. **`plan=` without `action=`** — auto-detect from the plan's current phase (see [Auto-Detect from Phase](#auto-detect-from-phase) below).
3. **`task=` or `issue=` without `action=`** — imply `action=init`. The supplied value becomes the plan source (`task` or `issue` respectively).
4. **`lesson=` without `action=`** — imply `action=lessons`. The supplied lesson ID seeds the lessons workflow.
5. **`recipe=` without `action=`** — imply `action=recipe`. The supplied recipe key seeds the recipe workflow.
6. **No source/target parameters at all** — default to `action=list` (interactive menu).

**Ambiguity guard**: if two or more *source-providing* parameters from {`task`, `issue`, `lesson`, `recipe`, `plan`} are supplied without an explicit `action=`, return `status: error` with a message naming the conflicting parameters and asking the user to either pass an explicit `action=` or remove one of the conflicting values.

### Action Routing

Once the action is resolved, load the appropriate workflow document and follow its instructions:

| Action | Workflow Document | Description |
|--------|-------------------|-------------|
| `list` (default) | `Read workflow/planning.md` | List all plans |
| `init` | `Read workflow/planning.md` | Create new plan, auto-continue to refine |
| `outline` | `Read workflow/planning-outline.md` | Run outline and plan phases |
| `cleanup` | `Read workflow/planning.md` | Remove completed plans |
| `lessons` | `Read workflow/planning.md` | List and convert lessons |
| `lessons-aggregate` | `Read workflow/planning-lessons-aggregate.md` | Aggressive cross-lesson aggregation + superseded-stub prune in a single command |
| `execute` | `Read workflow/execution.md` | Execute implementation tasks + verification |
| `finalize` | `Read workflow/execution.md` | Commit, push, PR |
| `recipe` | `Read workflow/recipe.md` | Create plan from predefined recipe |

### Auto-Detect from Phase

When `plan` is specified but no `action`, auto-detect from plan phase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-routing-context \
  --plan-id {plan_id}
```

| Current Phase | Workflow Document | Action |
|---------------|-------------------|--------|
| 1-init | `Read workflow/planning.md` | `init` |
| 2-refine | `Read workflow/planning.md` | `init` (continues refine) |
| 3-outline | `Read workflow/planning-outline.md` | `outline` |
| 4-plan | `Read workflow/planning-outline.md` | `outline` (continues plan) |
| 5-execute | `Read workflow/execution.md` | `execute` |
| 6-finalize | `Read workflow/execution.md` | `finalize` |

### Execution

After determining the action and workflow document:

1. **Read** the workflow document (`workflow/planning.md` or `workflow/execution.md`)
2. **Navigate** to the section for the resolved action
3. **Follow** the workflow instructions in that section

## Usage Examples

```bash
# List all plans (interactive selection)
/plan-marshall

# Create new plan from task description (action=init implied by task=)
/plan-marshall task="Add user authentication"

# Create new plan from GitHub issue (action=init implied by issue=)
/plan-marshall issue="https://github.com/org/repo/issues/42"

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

# Convert specific lesson to plan (action=lessons implied by lesson=)
/plan-marshall lesson="2026-05-18-11-001"

# Aggressive cross-lesson aggregation + superseded-stub prune in one batch
/plan-marshall action=lessons-aggregate

# Create plan from predefined recipe — lists available recipes for selection
/plan-marshall action=recipe

# Create plan from specific recipe (action=recipe implied by recipe=)
/plan-marshall recipe="refactor-to-standards"

# Explicit action= always wins over implicit inference
/plan-marshall action=init task="Add user authentication"
```

## Continuous Improvement

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with category `bug`, `improvement`, or `anti-pattern` and component in `{bundle}:{skill}` notation (e.g., `plan-marshall:manage-tasks`)

## Terminal Title Integration

The plan-marshall hooks can drive a live session-tab title (plan + phase + status icon). The writer side publishes `{plan_dir}/title-body.txt` on every status mutation — no user configuration is required. The reader side is implemented per-target by the platform runtime (`session render-title` operation); see `plan-marshall:platform-runtime` for the reader contract.

## Session ID Resolver

Main-context skill calls that need the current session ID (e.g., `phase-6-finalize` forwarding it to `manage-metrics enrich`) capture it via the platform-runtime `session capture` operation, which stores it in `status.json` at plan-init time. Retrieval: `manage-status metadata --get --field session_id`.

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
| `plan-marshall:execution-context` | Generic dispatcher: loads caller-specified skills + workflow doc and follows it |
