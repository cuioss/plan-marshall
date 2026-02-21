# Execution Workflows (Phases 5 & 7)

Workflows for plan execution phases: execute (task implementation + verification) and finalize (commit, PR).

## Action Routing

| Action | Workflow |
|--------|----------|
| `execute` (default) | Run execute phase (task iteration + verification) |
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

This workflow handles 5-execute/6-finalize phases only.
Use /plan-marshall to complete 1-init through 4-plan phases first.
```

---

## Execute Phase (DUMB LOOP Pattern)

The execute phase iterates through tasks using a simple loop:

```bash
# Get next pending task
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks next --plan-id {plan_id}

# After each step completion, finalize step
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks finalize-step --plan-id {plan_id} --task {task_number} --step {step_number} --outcome done
```

For each task:
1. Read task details via manage-tasks
2. Delegate to domain agent based on domain
3. Mark task complete
4. Repeat until all tasks done

### Execute Phase Completion

After all tasks complete, transition and check auto-continue:

```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} --completed 5-execute
```

**Config check** — Read `finalize_without_asking` to determine next action:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute get --field finalize_without_asking --trace-plan-id {plan_id}
```

**IF `finalize_without_asking == true`**:
- Log: `"(pm-workflow:plan-marshall) Config: finalize_without_asking=true — auto-continuing to finalize"`
- Continue to **Finalize Phase** below

**ELSE (default)**:
- Display: `"Execute phase complete. Ready to finalize."`
- Display: `"Run '/plan-marshall action=finalize plan={plan_id}' when ready."`
- **STOP**

### Domain Agent Routing

| Domain | Agent |
|--------|-------|
| `java` | `pm-dev-java:java-implement-agent` |
| `javascript` | `pm-dev-frontend:js-implement-agent` |
| `plan-marshall-plugin-dev` | No delegation (inline) |
| `generic` | No delegation (inline) |

---

## Finalize Phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (pm-workflow:plan-marshall) Loading pm-workflow:phase-6-finalize"
```

```
Skill: pm-workflow:phase-6-finalize
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
- Archive plan (move to `.plan/archived-plans/`)
- Mark lesson applied (if plan originated from a lesson)

### Finalize Validation

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-marshall plan="jwt-auth" action="finalize"
```
