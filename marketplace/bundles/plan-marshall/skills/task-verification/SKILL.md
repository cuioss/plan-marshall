---
name: task-verification
description: Verification-only task execution — runs commands without modifying files
user-invocable: false
---

# Task Verification Skill

**Role**: Task executor skill for verification-only tasks (profile=verification). Loaded by `plan-marshall:phase-5-execute` skill when `task.profile` is `verification`.

**Key Pattern**: No files are modified. Steps contain verification commands to run. Each step is executed and marked done/failed. No domain skills are needed.

## Contract Compliance

**MANDATORY**: Follow the contracts defined in:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Contract | `plan-marshall:manage-tasks/standards/task-contract.md` | Task structure, fields, status values, and JSON schema |
| Task Executor Base | `plan-marshall:ref-workflow-architecture/standards/task-executor-base.md` | Shared workflow steps for all task executors |

## Input / Output

See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for the common input contract and base output schema. This profile extends the base output with:

```toon
execution_summary:
  commands_run: [commands]
verification:
  exit_code: {exit_code}
  stderr: "{truncated stderr, max 2000 chars}"
  findings:
    - type: {compile-error|test-failure|lint-issue}
      file: {file_path}
      line: {line_number}
      message: "{error message}"
```

## Workflow

This skill follows the shared task executor workflow. Steps marked **[BASE]** are defined in [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md). Steps without the tag are verification-specific.

### Step 1: Load Task Context [BASE]

Follow the base workflow. Verify `profile` is `verification`. Steps contain verification commands (not file paths).

### Step 2: Execute Verification Steps

Steps are executed sequentially. For each step (verification command):

1. Run the command:
```bash
{step.target}
```

2. Check exit code and output

### Step 3: Mark Step Complete [BASE]

### Step 4: Handle Failures

**If a command fails**:
1. Analyze error output
2. This is a verification task — do NOT modify source files
3. Report the failure with structured output for triage

If verification fails:
```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --number {task_number} \
  --status blocked
```

### Step 5: Record Lessons [BASE]

Use component `"plan-marshall:task-verification"`. Record lessons on unexpected failures or environment issues.

### Step 6: Return Results

On **success**: Use the base output contract with `next_action: task_complete`.

On **failure** (structured output for phase-5-execute triage):

```toon
status: error
plan_id: {plan_id}
task_number: {task_number}
execution_summary:
  steps_completed: {N}
  steps_total: {M}
  commands_run:
    - {cmd1}
verification:
  passed: false
  command: "{failed command}"
  exit_code: {exit_code}
  stderr: "{truncated stderr, max 2000 chars}"
  findings:
    - type: {compile-error|test-failure|lint-issue}
      file: {file_path}
      line: {line_number}
      message: "{error message}"
next_action: requires_attention
```

The `findings` array is best-effort: parse compiler errors, test failures, or lint output into structured entries. If parsing fails, include the raw `stderr` for the triage step to analyze.

## Integration

**Invoked by**: `plan-marshall:phase-5-execute` skill (when task.profile = verification)

**Skill Loading**: Agent resolves this skill via `resolve-task-executor --profile verification`

**Script Notations**: See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for the complete list.
