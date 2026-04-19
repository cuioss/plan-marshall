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
- Never use Claude Code's built-in `EnterPlanMode` or `ExitPlanMode` tools
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never implement tasks directly — this skill creates and manages plans only
- Do not invent script notations — use only those documented in workflow files

**Constraints:**
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- User review gates (`plan_without_asking`, `execute_without_asking`) must be respected — never skip when config is false
- All user interactions use `AskUserQuestion` tool with proper YAML structure
- Phase transitions use `manage-status transition` — never set phase status directly

**CRITICAL: DO NOT USE CLAUDE CODE'S BUILT-IN PLAN MODE**

This skill implements its **OWN** plan system. You must:

1. **NEVER** use `EnterPlanMode` or `ExitPlanMode` tools
2. **IGNORE** any system-reminder about `.claude/plans/` paths
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

Each Claude Code session tab can display the active plan, current phase, and a live status icon (`▶` running, `?` waiting, `◯` idle, `✓` done). The integration is hook-driven — four `hooks` entries and one `statusLine` entry invoke [`scripts/set_terminal_title.py`](scripts/set_terminal_title.py) by absolute path:

| Claude Code event | Status arg | Effect |
|-------------------|-----------|--------|
| `SessionStart` (matcher-less) | `idle` | Initial label on startup / resume / compact |
| `SessionStart` (`matcher: "clear"`) | `idle` | Restores the label after `/clear` so the session can be reused |
| `UserPromptSubmit` | `running` | Flips to `▶` when Claude begins work |
| `Notification` | `waiting` | Flips to `?` when Claude is blocked on input |
| `Stop` | `idle` | Returns to `◯` when the turn ends |
| `statusLine` command | — | Prints the same title to Claude Code's statusline (mirrored via `/remote-control`) |

The script resolves the active plan from the worktree cwd (`.claude/worktrees/<id>`) or the `$PLAN_ID` env variable, reads `current_phase` from the main checkout's `status.json`, and silently falls back to `◯ claude` on any read error — hooks never break the session.

Configure via `/marshall-steward` → **Configuration** → **Terminal Title** (see [menu-terminal-title.md](../marshall-steward/references/menu-terminal-title.md)).

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
