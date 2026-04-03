---
name: task-verification
description: Verification-only task execution — runs commands without modifying files
user-invocable: false
---

# Task Verification Skill

**Role**: Task executor skill for verification-only tasks (profile=verification). Loaded by `plan-marshall:phase-5-execute` skill when `task.profile` is `verification`.

**Key Pattern**: No files are modified. Steps contain verification commands to run. Each step is executed and marked done/failed. No domain skills are needed.

**Base Contract**: This skill follows the task executor contract defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md). See that document for shared steps ([BASE] steps below), input/output contracts, error handling, and script notations.

**Note**: The `verification` profile is distinct from the `verification` change-type (see [change-types.md](../ref-workflow-architecture/standards/change-types.md)). The profile determines HOW a task executes (run commands, don't modify files); the change-type describes WHY a request was made (validate/confirm something).

## Output Extensions

This profile extends the base output with:

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

Steps marked **[BASE]** are defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md).

### Step 1: Load Task Context [BASE]

Verify `profile` is `verification`. Steps contain verification commands (not file paths).

### Step 2: Execute Verification Steps

Steps are executed sequentially. For each step (verification command):

1. Run the command (with a 5-minute timeout):
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
