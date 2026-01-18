---
name: plan-execute
description: Execute task plans - execute and finalize phases
user-invocable: true
allowed-tools: Read, Skill, Bash, AskUserQuestion, Task
---

# Plan Execute Skill

Execute task plans through the execute phase (task implementation) and finalize phase (commit, PR).

## 5-Phase Model

```
1-init → 2-outline → 3-plan → 4-execute → 5-finalize
```

This skill handles **4-execute** and **5-finalize** phases. Use `/plan-manage` for 1-init, 2-outline, and 3-plan phases.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `plan` | optional | Plan name to execute (e.g., `jwt-auth`, not path) |
| `action` | optional | Explicit action: `execute`, `finalize` (default: execute) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## Workflow

### Action Routing

Route based on action parameter:
- `execute` (default) → Run execute phase (task iteration)
- `finalize` → Run finalize phase (commit, PR)

### Default (no parameters)

Shows executable plans for selection:

```
Executable Plans:

1. jwt-authentication [execute] - Task 3/12: "Add token validation"
2. user-profile-api [finalize] - Ready to commit

0. Exit (use /plan-manage to create or refine plans)

Select plan to execute:
```

### With plan parameter

Execute specific plan from its current phase:

If plan is in 1-init, 2-outline, or 3-plan phase:
```
Plan 'jwt-auth' is in '2-outline' phase.

This skill handles 4-execute/5-finalize phases only.
Use /plan-manage to complete 1-init/2-outline/3-plan phases first.
```

---

## Execute Phase (DUMB LOOP Pattern)

The execute phase iterates through tasks using a simple loop:

```bash
# Get next pending task
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks next --plan-id {plan_id}

# After task completion, mark done
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks check --plan-id {plan_id} --number {task_number} --status done
```

For each task:
1. Read task details via manage-tasks
2. Delegate to domain agent based on domain
3. Mark task complete
4. Repeat until all tasks done

### Domain Agent Routing

| Domain | Agent |
|--------|-------|
| `java` | `pm-dev-java:java-implement-agent` |
| `javascript` | `pm-dev-frontend:js-implement-agent` |
| `plan-marshall-plugin-dev` | No delegation (inline) |
| `generic` | No delegation (inline) |

---

## Finalize Phase

```
Skill: pm-workflow:phase-5-finalize
operation: finalize
plan_id: {plan_id}
```

Handles:
- Run verification (if configured)
- Commit changes
- Push to remote
- Create PR (if configured)
- Run PR workflow (if configured)
- Mark plan complete

### Finalize Validation

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-execute plan="jwt-auth" action="finalize"
```

---

## Usage Examples

```bash
# Select from executable plans (interactive)
/plan-execute

# Execute specific plan (continues current phase)
/plan-execute plan="jwt-auth"

# Run finalize phase directly
/plan-execute plan="jwt-auth" action="finalize"
```

## Related

| Skill | Purpose |
|-------|---------|
| `pm-workflow:plan-manage` | Manage plans (init, outline, list, cleanup) |
| `pm-workflow:manage-tasks` | Task iteration (next, check) |
| `pm-workflow:phase-5-finalize` | Finalize phase execution |

| Agent | Purpose |
|-------|---------|
| `pm-dev-java:java-implement-agent` | Java task implementation |
| `pm-dev-frontend:js-implement-agent` | JavaScript task implementation |
