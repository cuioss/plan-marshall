---
name: task-module-testing
description: Domain-agnostic module testing task execution with two-tier skill loading
user-invocable: false
---

# Task Module Testing Skill

**Role**: Domain-agnostic task executor skill for executing module testing tasks (profile=module_testing). Loaded by `plan-marshall:phase-5-execute` skill when `task.profile` is `module_testing`.

**Key Pattern**: Agent loads this skill via `resolve-task-executor --profile module_testing`. Skill executes a test-focused workflow: understand context → plan tests → implement tests → verify. Domain-specific testing knowledge comes from `task.skills` (loaded by agent).

**Base Contract**: This skill follows the task executor contract defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md). See that document for shared steps ([BASE] steps below), input/output contracts, error handling, integration points, and script notations.

## Output Extensions

This profile extends the base output with:

```toon
execution_summary:
  tests_written: N
  coverage_impact: {if available}
verification:
  tests_passed: N
  tests_failed: N
```

## Workflow

Steps marked **[BASE]** are defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md) — follow them exactly.

### Step 1: Load Task Context [BASE]

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get \
  --plan-id {plan_id} --number {task_number}
```

Verify `profile` is `module_testing`.

### Step 2: Understand Implementation Context

Before writing tests, understand what is being tested. Use `Grep` and `Glob` tools to find the implementation files corresponding to each test file in the steps. Use the `Read` tool to examine them.

Identify testable elements:
- Public methods/functions
- Edge cases and error conditions
- Input validation
- Integration points
- Configuration behaviors

### Step 3: Plan Test Implementation

For each step (test file path), determine:
- What test scenarios to cover
- Test structure (unit vs integration) — follow patterns from loaded domain skills
- Assertions needed
- Setup/teardown requirements

### Step 4: Implement Tests

For each step (test file path):

- **Create new test file**: Use the `Write` tool. Apply testing patterns from domain skills (e.g., `pm-dev-java:junit-core`, `pm-dev-frontend:jest-testing`). Follow the AAA pattern (Arrange-Act-Assert).
- **Modify existing test file**: Use the `Edit` tool. Add new test methods, maintain existing test structure.

Include positive and negative test cases with descriptive test names.

### Step 5: Mark Step Complete [BASE]

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} --task {task_number} --step {N} --outcome done
```

### Step 6: Run Verification [BASE]

Module testing tasks run the full test suite for the module, not targeted test classes. The safety net resolve command is `module-tests`.

### Step 7: Handle Verification Results [BASE]

On test failure:
1. Determine if test logic is wrong or implementation has a bug
2. If test logic issue → fix test
3. If implementation bug discovered → fix the production code AND the test. Adapting production code to make tests pass is expected within module_testing tasks.

### Step 8: Record Lessons [BASE]

Use component `"plan-marshall:task-module-testing"`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:task-module-testing" --category improvement \
  --title "{issue summary}" --detail "{context and resolution}"
```

### Step 9: Return Results [BASE]

Include the additional `tests_written`, `tests_passed`, and `tests_failed` fields.

## Profile-Specific Error Handling

### Implementation Not Found

If implementation to test doesn't exist:
- Check if implementation task is in dependencies
- If yes, mark task as blocked
- If no, note in lessons learned
