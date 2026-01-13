---
name: plan-execute
description: Execute task plans - execute and finalize phases
tools: Read, Skill, Bash, AskUserQuestion, Task
---

# Plan Execute Command

Execute task plans through the execute phase (task implementation) and finalize phase (commit, PR).

## 5-Phase Model

```
1-init → 2-outline → 3-plan → 4-execute → 5-finalize
```

This command handles **4-execute** and **5-finalize** phases. Use `/plan-manage` for 1-init, 2-outline, and 3-plan phases.

## PARAMETERS

| Parameter | Type | Description |
|-----------|------|-------------|
| `plan` | optional | Plan name to execute (e.g., `jwt-auth`, not path) |
| `action` | optional | Explicit action: `execute`, `finalize` (default: execute) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## WORKFLOW

1. **Load manage-lifecycle skill**:
   ```
   Skill: pm-workflow:manage-lifecycle
   ```

2. **Route based on action**:
   - `execute` → Run execute phase (task iteration)
   - `finalize` → Run finalize phase (commit, PR)

### Execute Phase (DUMB LOOP Pattern)

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

### Finalize Phase

```
Skill: pm-workflow:phase-5-finalize
operation: finalize
plan_id: {plan_id}
```

Handles: verification, commit, push, PR creation, PR workflow

## BEHAVIOR

### Default (no parameters)

Shows executable plans for selection:

```
/plan-execute
```

Shows:
```
Executable Plans:

1. jwt-authentication [execute] - Task 3/12: "Add token validation"
2. user-profile-api [finalize] - Ready to commit

0. Exit (use /plan-manage to create or refine plans)

Select plan to execute:
```

### With plan parameter

Execute specific plan from its current phase:

```
/plan-execute plan="jwt-auth"
```

If plan is in 1-init, 2-outline, or 3-plan phase:
```
Plan 'jwt-auth' is in '2-outline' phase.

This command handles 4-execute/5-finalize phases only.
Use /plan-manage to complete 1-init/2-outline/3-plan phases first.
```

### With action parameter

Force specific action:

```
/plan-execute plan="jwt-auth" action="finalize"
```

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-execute plan="jwt-auth" action="finalize"
```

## USAGE EXAMPLES

```bash
# Select from executable plans (interactive)
/plan-execute

# Execute specific plan (continues current phase)
/plan-execute plan="jwt-auth"

# Run finalize phase directly
/plan-execute plan="jwt-auth" action="finalize"
```

## PHASE EXECUTION

### Execute Phase

Executes implementation tasks using DUMB LOOP pattern:

1. Get next pending task via `manage-tasks:next`
2. Read task details (title, specification, steps)
3. Delegate to domain agent based on domain:
   - `java` → `pm-dev-java:java-implement-agent`
   - `javascript` → `pm-dev-frontend:js-implement-agent`
   - `plan-marshall-plugin-dev` → No delegation (inline)
   - `generic` → No delegation (inline)
4. Mark task complete via `manage-tasks:check`
5. Repeat until all tasks done
6. Transition to finalize phase

### Finalize Phase

Completes the plan via `pm-workflow:phase-5-finalize` skill:
- Run verification (if configured)
- Commit changes
- Push to remote
- Create PR (if configured)
- Run PR workflow (if configured)
- Mark plan complete

## RELATED

| Command | Relationship |
|---------|--------------|
| `/plan-manage` | Manage plans (init, refine, list, cleanup) |

| Skill | Purpose |
|-------|---------|
| `pm-workflow:manage-lifecycle` | Plan discovery, phase routing, transitions |
| `pm-workflow:manage-tasks` | Task iteration (next, check) |
| `pm-workflow:phase-5-finalize` | Finalize phase execution |

| Agent | Purpose |
|-------|---------|
| `pm-dev-java:java-implement-agent` | Java task implementation |
| `pm-dev-frontend:js-implement-agent` | JavaScript task implementation |
