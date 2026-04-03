---
name: task-executor
description: Domain-agnostic task execution with profile-based workflow selection (implementation, module_testing, verification)
user-invocable: false
---

# Task Executor Skill

**Role**: Unified, domain-agnostic workflow skill for executing tasks during phase-5-execute. Handles all profiles: `implementation`, `module_testing`, and `verification`. Loaded by `plan-marshall:phase-5-execute` when executing any task.

**Key Pattern**: Agent loads this skill via `resolve-task-executor --profile {profile}`. Skill reads the task's profile and follows the appropriate workflow. Domain-specific knowledge comes from `task.skills` (loaded by agent).

**Base Contract**: This skill follows the task executor contract defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md) for input/output contracts, error handling, and script notations.

---

## Common Workflow

All profiles share these steps. Profile-specific steps are documented in each profile section below.

### Step: Load Task Context

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get \
  --plan-id {plan_id} --number {task_number}
```

Extract key fields: `domain`, `profile`, `skills`, `description`, `steps`, `verification`, `depends_on`. Verify `profile` matches the expected profile for this execution.

### Step: Mark Step Complete

After completing each step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} --task {task_number} --step {N} --outcome done
```

### Step: Run Verification

After all steps complete, run task verification using commands from `task.verification.commands`.

**Safety net** (should not trigger in normal operation): If verification commands are missing, log a WARN and resolve from architecture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[VERIFY] (plan-marshall:task-executor) TASK-{N} missing verification — falling back to architecture resolve"

python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command {resolve_command} --name {module} \
  --trace-plan-id {plan_id}
```

Where `{resolve_command}` depends on profile: `implementation` → `compile`, `module_testing` → `module-tests`. Verification profile uses commands from task steps directly.

### Step: Handle Verification Results

**If verification passes**: Mark task done via `manage-tasks update --status done`.

**If verification fails**:
1. Analyze error output and identify failing component
2. Fix the issue (see profile-specific scope below)
3. Re-run verification
4. Iterate until pass (max `verification_max_iterations` from config, default 5)

If still failing after max iterations: mark task as `blocked` and record details in work.log.

### Step: Record Lessons

On issues or unexpected patterns:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:task-executor" --category improvement \
  --title "{issue summary}" --detail "{context and resolution}"
```

### Step: Return Results

Base output contract (profile-specific extensions noted in each section):

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

## Profile: implementation

Production code creation and modification.

### Compatibility Strategy

Before implementing, read the compatibility approach:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

**No fallback** — if field not found, fail with error and abort task.

Apply throughout all subsequent steps:

- **breaking**: Make changes directly. Remove old code, rename freely, no backward compatibility.
- **deprecation**: Keep old APIs/methods with `@Deprecated` markers. Add new code alongside old. Provide migration notes in commit messages.
- **smart_and_ask**: For each change that could break consumers, evaluate impact. If uncertain, ask user via AskUserQuestion before proceeding.

### Workflow

1. **Understand Context**: Read affected files (`step.target`) if they exist. Use `Grep` and `Glob` to find related components. Apply domain knowledge from loaded skills.
2. **Plan Implementation**: For each step, determine changes needed, domain skill patterns to apply, modification order, and integration considerations.
3. **Implement Changes**: For each step — create new files with `Write`, modify existing files with `Edit`. Apply domain patterns and maintain existing code style.
4. **Mark Step Complete** (common step)
5. **Run Verification** — resolve command: `compile` (compilability only — full tests belong to module_testing)
6. **Handle Verification Results** — fix scope: production code
7. **Record Lessons**, **Return Results**

### Error Handling

| Failure | Action |
|---------|--------|
| Conflicting changes | Analyze conflict, prefer preserving existing behavior, ask for clarification if needed |

---

## Profile: module_testing

Unit and module test creation.

### Workflow

1. **Understand Implementation Context**: Use `Grep` and `Glob` to find implementation files corresponding to each test file in steps. Read and examine them. Identify testable elements: public methods, edge cases, error conditions, input validation, integration points.
2. **Plan Test Implementation**: For each step, determine test scenarios, test structure (unit vs integration per domain skills), assertions needed, setup/teardown requirements.
3. **Implement Tests**: For each step — create new test files with `Write`, modify existing test files with `Edit`. Follow the AAA pattern (Arrange-Act-Assert). Include positive and negative test cases with descriptive names.
4. **Mark Step Complete** (common step)
5. **Run Verification** — resolve command: `module-tests` (full test suite for the module)
6. **Handle Verification Results** — on test failure: determine if test logic is wrong or implementation has a bug. If test logic → fix test. If implementation bug → fix production code AND the test. Adapting production code to make tests pass is expected within this profile.
7. **Record Lessons**, **Return Results**

### Output Extensions

```toon
execution_summary:
  tests_written: N
  coverage_impact: {if available}
verification:
  tests_passed: N
  tests_failed: N
```

### Error Handling

| Failure | Action |
|---------|--------|
| Implementation not found | Check if implementation task is in dependencies. If yes → mark task as blocked. If no → note in lessons learned |

---

## Profile: verification

Run verification commands without modifying files.

**Note**: The `verification` profile is distinct from the `verification` change-type (see [change-types.md](../ref-workflow-architecture/standards/change-types.md)). The profile determines HOW a task executes; the change-type describes WHY a request was made.

### Workflow

1. **Execute Verification Steps**: Steps contain verification commands (not file paths). Execute sequentially. For each step, run `{step.target}` and check exit code and output.
2. **Mark Step Complete** (common step)
3. **Handle Failures**: This is a verification task — do NOT modify source files. Report failures with structured output for triage. If verification fails, mark task as `blocked`.
4. **Record Lessons** (on unexpected failures or environment issues), **Return Results**

No domain skills are needed for this profile.

### Output Extensions

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

On **success**: `next_action: task_complete`.
On **failure**: `status: error`, `next_action: requires_attention`, plus the extension fields. The `findings` array is best-effort: parse compiler errors, test failures, or lint output into structured entries. If parsing fails, include the raw `stderr`.
