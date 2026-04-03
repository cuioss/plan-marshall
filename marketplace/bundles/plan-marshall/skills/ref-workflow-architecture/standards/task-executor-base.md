# Task Executor Base Workflow

Shared workflow steps for all task executor skills (task-implementation, task-module-testing, task-verification). Profile-specific skills define their unique steps and reference this document for the common steps.

---

## Common Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task number to execute |

---

## Shared Workflow Steps

### Load Task Context

Read the task file to understand what needs to be done:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get \
  --plan-id {plan_id} \
  --number {task_number}
```

Extract key fields:
- `domain`: Domain for this task
- `profile`: Should match the expected profile for this executor
- `skills`: Domain skills to apply (already loaded by agent)
- `description`: What to do
- `steps`: File paths (or commands for verification profile) to work on
- `verification`: How to verify success
- `depends_on`: Dependencies (should be complete)

**Note**: Steps are executed sequentially. No explicit "in_progress" marker is needed — proceed directly to execution.

---

### Mark Step Complete

After completing each step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task {task_number} \
  --step {N} \
  --outcome done
```

---

### Run Verification

After all steps complete, run task verification.

Execute the verification commands from `task.verification.commands`. Every task SHOULD have commands populated by the plan phase (copied from the deliverable).

**Safety net** (should not trigger in normal operation): If verification commands are missing, log a WARN and resolve from architecture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[VERIFY] ({skill_name}) TASK-{N} missing verification — falling back to architecture resolve"

python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command {resolve_command} --name {module} \
  --trace-plan-id {plan_id}
```

Where `{resolve_command}` depends on the profile:
- `implementation` → `compile`
- `module_testing` → `module-tests`

---

### Handle Verification Results

**If verification passes**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --number {task_number} \
  --status done
```

**If verification fails**:

1. Analyze error output
2. Identify failing component
3. Fix the issue (profile-specific — see executor skill for scope)
4. Re-run verification
5. Iterate until pass (max 3 iterations)

If still failing after 3 iterations:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --number {task_number} \
  --status blocked
```

Record details in work.log using manage-log.

---

### Record Lessons

On issues or unexpected patterns:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{skill_notation}" \
  --category improvement \
  --title "{issue summary}" \
  --detail "{context and resolution}"
```

**Valid categories**: `bug`, `improvement`, `anti-pattern`

---

### Return Results

Base output contract (profile-specific executors may add additional fields):

```toon
status: success | error
plan_id: {echo}
task_number: {echo}
execution_summary:
  steps_completed: N
  steps_total: M
  files_modified: [paths]
verification:
  passed: true | false
  command: "{cmd}"
next_action: task_complete | requires_attention
message: {error message if status=error}
```

---

## Common Error Handling

### Missing Dependency

If a file depends on code not yet implemented:
- Check if dependency is in a later step
- If yes, reorder steps
- If no, create minimal stub and note

### Verification Timeout

If verification command hangs:
- Kill after 5 minutes
- Record timeout in lessons
- Try with reduced scope

---

## Common Script Notations

All task executor skills use these notations (use EXACTLY as shown):

| Notation | Purpose |
|----------|---------|
| `plan-marshall:manage-tasks:manage-tasks` | Task operations (get, update, finalize-step) |
| `plan-marshall:manage-lessons:manage-lessons` | Record lessons (add) |
| `plan-marshall:manage-logging:manage-logging` | Logging (work) |
| `plan-marshall:manage-config:manage-config` | Read project configuration |
| `plan-marshall:manage-architecture:architecture` | Build command resolution (verification fallback) |
