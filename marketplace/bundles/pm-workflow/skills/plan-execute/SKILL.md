---
name: plan-execute
description: Execute task plans - execute and finalize phases
user-invocable: false
allowed-tools: Read, Skill, Bash, AskUserQuestion, Task
---

# Plan Execute Skill

Execute task plans through the execute phase (task implementation), verify phase (quality checks), and finalize phase (commit, PR).

## 7-Phase Model

```
1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-verify → 7-finalize
```

This skill handles **5-execute**, **6-verify**, and **7-finalize** phases. Use `/plan-marshall` for 1-init through 4-plan phases.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `plan` | optional | Plan name to execute (e.g., `jwt-auth`, not path) |
| `action` | optional | Explicit action: `execute`, `verify`, `finalize` (default: execute) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## Workflow

### Action Routing

Route based on action parameter:
- `execute` (default) → Run execute phase (task iteration)
- `verify` → Run verify phase (quality checks)
- `finalize` → Run finalize phase (commit, PR)

### Default (no parameters)

Shows executable plans for selection:

```
Executable Plans:

1. jwt-authentication [execute] - Task 3/12: "Add token validation"
2. user-profile-api [finalize] - Ready to commit

0. Exit (use /plan-marshall to create or refine plans)

Select plan to execute:
```

### With plan parameter

Execute specific plan from its current phase:

If plan is in 1-init, 3-outline, or 4-plan phase:
```
Plan 'jwt-auth' is in '3-outline' phase.

This skill handles 5-execute/6-verify/7-finalize phases only.
Use /plan-marshall to complete 1-init through 4-plan phases first.
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

## Verify Phase

Load the verify phase skill:

```
Skill: pm-workflow:phase-6-verify
```

**Input**: `plan_id`

The verify skill handles:
- Quality check (lint, format, analysis)
- Build verify (compile, tests)
- Technical implementation verification
- Technical test verification
- Documentation sync (advisory)
- Formal spec drift check

On findings: Creates fix tasks and loops back to execute phase (max 5 iterations).

---

## Finalize Phase

```
Skill: pm-workflow:phase-7-finalize
operation: finalize
plan_id: {plan_id}
```

Handles:
- Commit and push changes
- Create PR (if configured)
- Automated review (CI, bot feedback)
- Sonar roundtrip (if configured)
- Knowledge capture (advisory)
- Lessons capture (advisory)
- Mark plan complete

### Finalize Validation

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-marshall plan="jwt-auth" action="finalize"
```

---

## Usage Examples

This skill is invoked internally by `pm-workflow:plan-marshall`. User-facing commands:

```bash
# Select from executable plans (interactive)
/plan-marshall

# Execute specific plan (continues current phase)
/plan-marshall plan="jwt-auth"

# Run verify phase
/plan-marshall plan="jwt-auth" action="verify"

# Run finalize phase directly
/plan-marshall plan="jwt-auth" action="finalize"
```

## Related

| Skill | Purpose |
|-------|---------|
| `pm-workflow:plan-manage` | Manage plans (init, outline, list, cleanup) |
| `pm-workflow:manage-tasks` | Task iteration (next, check) |
| `pm-workflow:phase-6-verify` | Verify phase execution |
| `pm-workflow:phase-7-finalize` | Finalize phase execution |

| Agent | Purpose |
|-------|---------|
| `pm-dev-java:java-implement-agent` | Java task implementation |
| `pm-dev-frontend:js-implement-agent` | JavaScript task implementation |
