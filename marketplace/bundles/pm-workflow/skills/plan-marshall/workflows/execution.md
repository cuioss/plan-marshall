# Execution Workflows (Phases 5-7)

Workflows for plan execution phases: execute (task implementation), verify (quality checks), and finalize (commit, PR).

## Action Routing

| Action | Workflow |
|--------|----------|
| `execute` (default) | Run execute phase (task iteration) |
| `verify` | Run verify phase (quality checks) |
| `finalize` | Run finalize phase (commit, PR) |

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

This workflow handles 5-execute/6-verify/7-finalize phases only.
Use /plan-marshall to complete 1-init through 4-plan phases first.
```

---

## Execute Phase (DUMB LOOP Pattern)

The execute phase iterates through tasks using a simple loop:

```bash
# Get next pending task
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks next --plan-id {plan_id}

# After each step completion, mark step done
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks step-done --plan-id {plan_id} --task {task_number} --step {step_number}
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
