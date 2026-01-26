---
name: plan-marshall
description: Unified plan lifecycle management - create, outline, execute, verify, and finalize plans
user-invocable: true
allowed-tools: Read, Skill, Bash, AskUserQuestion, Task
---

# Plan Marshall Skill

Unified entry point for plan lifecycle management. Routes to the appropriate internal skill based on action and plan phase.

**CRITICAL: DO NOT USE CLAUDE CODE'S BUILT-IN PLAN MODE**

This skill implements its **OWN** plan system. You must:

1. **NEVER** use `EnterPlanMode` or `ExitPlanMode` tools
2. **IGNORE** any system-reminder about `.claude/plans/` paths
3. **ONLY** use plans via `pm-workflow:manage-*` skills

## 7-Phase Model

```
1-init -> 2-refine -> 3-outline -> 4-plan -> 5-execute -> 6-verify -> 7-finalize
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | optional | Explicit action: `list`, `init`, `outline`, `execute`, `verify`, `finalize`, `cleanup`, `lessons` (default: list) |
| `task` | optional | Task description for creating new plan |
| `issue` | optional | GitHub issue URL for creating new plan |
| `lesson` | optional | Lesson ID to convert to plan |
| `plan` | optional | Plan name for specific operations (e.g., `jwt-auth`, not path) |
| `stop-after-init` | optional | If true, stop after 1-init phase without continuing to 2-refine (default: false) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## Workflow

### Action Routing

Route based on action parameter:

| Action | Routes To | Description |
|--------|-----------|-------------|
| `list` (default) | `pm-workflow:plan-manage` | List all plans |
| `init` | `pm-workflow:plan-manage` | Create new plan, auto-continue to refine |
| `outline` | `pm-workflow:plan-manage` | Run outline and plan phases |
| `execute` | `pm-workflow:plan-execute` | Execute implementation tasks |
| `verify` | `pm-workflow:plan-execute` | Run quality verification |
| `finalize` | `pm-workflow:plan-execute` | Commit, push, PR |
| `cleanup` | `pm-workflow:plan-manage` | Remove completed plans |
| `lessons` | `pm-workflow:plan-manage` | List and convert lessons |

### Auto-Detection (plan parameter without action)

When `plan` is specified but no `action`, auto-detect from plan phase:

```bash
python3 .plan/execute-script.py pm-workflow:plan-manage:manage-lifecycle get-routing-context \
  --plan-id {plan_id}
```

| Current Phase | Routes To | Action |
|---------------|-----------|--------|
| 1-init | `pm-workflow:plan-manage` | `init` |
| 2-refine | `pm-workflow:plan-manage` | `init` (continues refine) |
| 3-outline | `pm-workflow:plan-manage` | `outline` |
| 4-plan | `pm-workflow:plan-manage` | `outline` (continues plan) |
| 5-execute | `pm-workflow:plan-execute` | `execute` |
| 6-verify | `pm-workflow:plan-execute` | `verify` |
| 7-finalize | `pm-workflow:plan-execute` | `finalize` |

### Execution

After routing, activate the target skill with the resolved action and all parameters:

**For phases 1-4**:
```
Skill: pm-workflow:plan-manage
```
Pass: action, task, issue, lesson, plan, stop-after-init as applicable.

**For phases 5-7**:
```
Skill: pm-workflow:plan-execute
```
Pass: action, plan as applicable.

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

# Run verification
/plan-marshall action=verify plan="jwt-auth"

# Finalize (commit, PR)
/plan-marshall action=finalize plan="jwt-auth"

# Auto-detect: continues from current phase
/plan-marshall plan="jwt-auth"

# Cleanup completed plans
/plan-marshall action=cleanup

# List lessons and convert to plan
/plan-marshall action=lessons
```

## Continuous Improvement

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with component: `{type: "skill", name: "plan-marshall", bundle: "pm-workflow"}`

## Related

| Skill | Purpose |
|-------|---------|
| `pm-workflow:plan-manage` | Internal: phases 1-4 (init, refine, outline, plan, list, cleanup, lessons) |
| `pm-workflow:plan-execute` | Internal: phases 5-7 (execute, verify, finalize) |
| `pm-workflow:workflow-extension-api` | Extension points for domain customization |
