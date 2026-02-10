---
name: task-verification
description: Verification-only task execution — runs commands without modifying files
user-invocable: false
allowed-tools: Bash
---

# Task Verification Skill

**Role**: Task executor skill for verification-only tasks (profile=verification). Loaded by `pm-workflow:task-execute-agent` when `task.profile` is `verification`.

**Key Pattern**: No files are modified. Steps contain verification commands to run. Each step is executed and marked done/failed. No domain skills are needed.

## Contract Compliance

**MANDATORY**: Follow the execution contract defined in:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Contract | `pm-workflow:manage-tasks/standards/task-contract.md` | Task structure and fields |

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task number to execute |

## Output

```toon
status: success | error
plan_id: {echo}
task_number: {echo}
execution_summary:
  steps_completed: N
  steps_total: M
  commands_run: [commands]
verification:
  passed: true | false
  command: "{cmd}"
next_action: task_complete | requires_attention
message: {error message if status=error}
```

## Workflow

### Step 1: Load Task Context

Read the task file:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get \
  --plan-id {plan_id} \
  --number {task_number}
```

Extract key fields:
- `profile`: Should be `verification`
- `steps`: Verification commands to run
- `verification`: Verification criteria

### Step 2: Execute Verification Steps

For each step (verification command):

1. Run the command:
```bash
{step.title}
```

2. Check exit code and output
3. Mark step complete:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task {task_number} \
  --step {N} \
  --outcome done
```

### Step 3: Handle Failures

**If a command fails**:
1. Analyze error output
2. This is a verification task — do NOT modify source files
3. Report the failure clearly

If verification fails:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --number {task_number} \
  --status blocked
```

### Step 4: Return Results

```toon
status: success
plan_id: {plan_id}
task_number: {task_number}
execution_summary:
  steps_completed: {N}
  steps_total: {M}
  commands_run:
    - {cmd1}
verification:
  passed: true
  command: "{verification command}"
next_action: task_complete
```

## Integration

**Invoked by**: `pm-workflow:task-execute-agent` (when task.profile = verification)

**Skill Loading**: Agent resolves this skill via `resolve-task-executor --profile verification`

**Script Notations** (use EXACTLY as shown):
- `pm-workflow:manage-tasks:manage-tasks` - Task operations (get, update, finalize-step)
