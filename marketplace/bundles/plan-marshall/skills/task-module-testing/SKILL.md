---
name: task-module-testing
description: Domain-agnostic module testing task execution with two-tier skill loading
user-invocable: false
---

# Task Module Testing Skill

**Role**: Domain-agnostic task executor skill for executing module testing tasks (profile=module_testing). Loaded by `plan-marshall:phase-5-execute` skill when `task.profile` is `module_testing`.

**Key Pattern**: Agent loads this skill via `resolve-task-executor --profile module_testing`. Skill executes a test-focused workflow: understand context → plan tests → implement tests → verify. Domain-specific testing knowledge comes from `task.skills` (loaded by agent).

## Contract Compliance

**MANDATORY**: Follow the contracts defined in:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Contract | `plan-marshall:manage-tasks/standards/task-contract.md` | Task structure, fields, status values, and JSON schema |
| Task Executor Base | `plan-marshall:ref-workflow-architecture/standards/task-executor-base.md` | Shared workflow steps for all task executors |

## Two-Tier Skill Loading

See [ref-workflow-architecture:skill-loading](../ref-workflow-architecture/standards/skill-loading.md) for the complete two-tier skill loading pattern. Agent loads Tier 1 (system skills) automatically, then Tier 2 (domain skills from `task.skills`). This workflow skill defines HOW the agent executes tests.

## Input / Output

See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for the common input contract and base output schema. This profile extends the base output with:

```toon
execution_summary:
  tests_written: N
  coverage_impact: {if available}
verification:
  tests_passed: N
  tests_failed: N
```

## Workflow

This skill follows the shared task executor workflow. Steps marked **[BASE]** are defined in [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) — follow them exactly. Steps without the tag are testing-specific.

### Step 1: Load Task Context [BASE]

Follow the base workflow. Verify `profile` is `module_testing`.

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

### Step 6: Run Verification [BASE]

Module testing tasks run the full test suite for the module, not targeted test classes. The safety net resolve command is `module-tests`.

### Step 7: Handle Verification Results [BASE]

On test failure:
1. Determine if test logic is wrong or implementation has a bug
2. If test logic issue → fix test
3. If implementation bug discovered → fix the production code AND the test. Adapting production code to make tests pass is expected within module_testing tasks.

### Step 8: Record Lessons [BASE]

Use component `"plan-marshall:task-module-testing"`.

### Step 9: Return Results [BASE]

Include the additional `tests_written`, `tests_passed`, and `tests_failed` fields.

## Error Handling

See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for common error handling (missing dependencies, verification timeout).

### Implementation Not Found

If implementation to test doesn't exist:
- Check if implementation task is in dependencies
- If yes, mark task as blocked
- If no, note in lessons learned

## Integration

**Invoked by**: `plan-marshall:phase-5-execute` skill (when task.profile = module_testing)

**Skill Loading**: Agent resolves this skill via `resolve-task-executor --profile module_testing`

**Script Notations**: See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for the complete list.
