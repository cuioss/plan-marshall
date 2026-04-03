---
name: task-implementation
description: Domain-agnostic implementation task execution with two-tier skill loading
user-invocable: false
---

# Task Implementation Skill

**Role**: Domain-agnostic workflow skill for executing implementation tasks (profile=implementation). Loaded by `plan-marshall:phase-5-execute` skill when `task.profile` is `implementation`.

**Key Pattern**: Agent loads this skill via `resolve-task-executor --profile implementation`. Skill executes a generic workflow: understand context → plan → implement → verify. Domain-specific knowledge comes from `task.skills` (loaded by agent).

**Base Contract**: This skill follows the task executor contract defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md). See that document for shared steps ([BASE] steps below), input/output contracts, error handling, integration points, and script notations.

**Output Extensions**: None — this profile uses the base output contract as-is.

## Workflow

Steps marked **[BASE]** are defined in [task-executors.md](../ref-workflow-architecture/standards/task-executors.md) — follow them exactly.

### Step 1: Load Task Context [BASE]

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get \
  --plan-id {plan_id} --number {task_number}
```

Verify `profile` is `implementation`.

### Step 2: Read Compatibility Strategy

Read the compatibility approach from marshal.json project configuration:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

**No fallback** — if field not found, fail with error and abort task.

Extract `compatibility` from the output. Apply throughout all subsequent steps:

- **breaking**: Make changes directly. Remove old code, rename freely, no backward compatibility.
- **deprecation**: Keep old APIs/methods with `@Deprecated` markers. Add new code alongside old. Provide migration notes in commit messages.
- **smart_and_ask**: For each change that could break consumers, evaluate impact. If uncertain, ask user via AskUserQuestion before proceeding.

### Step 3: Understand Context

Before implementing, understand the codebase context:

**Read affected files** (from steps): Use the `Read` tool on each `step.target` if the file exists.

**Read related files**: Use `Grep` and `Glob` tools to find related components, then `Read` them.

**Apply domain knowledge**: Reference patterns from loaded domain skills, understand project conventions, identify dependencies and integration points.

### Step 4: Plan Implementation

For each step (file path), determine what changes are needed, how to apply domain skill patterns, order of modifications, and integration considerations.

### Step 5: Implement Changes

For each step (file path):

- **Create new file**: Use the `Write` tool. Apply patterns from domain skills, follow project conventions.
- **Modify existing file**: Use the `Edit` tool. Apply changes following domain skill patterns, maintain existing code style.

### Step 6: Mark Step Complete [BASE]

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} --task {task_number} --step {N} --outcome done
```

### Step 7: Run Verification [BASE]

Implementation tasks verify compilability only — full test execution belongs to module_testing profile. The safety net resolve command is `compile`.

### Step 8: Handle Verification Results [BASE]

On failure: analyze error output, identify failing component, fix the issue, re-run verification (max `verification_max_iterations` from config, default 5).

### Step 9: Record Lessons [BASE]

Use component `"plan-marshall:task-implementation"`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:task-implementation" --category improvement \
  --title "{issue summary}" --detail "{context and resolution}"
```

### Step 10: Return Results [BASE]

## Profile-Specific Error Handling

### Conflicting Changes

If changes conflict with existing code:
- Analyze conflict
- Prefer preserving existing behavior
- Ask for clarification if needed

## Additional Script Notations

- `plan-marshall:manage-config:manage-config` — Read compatibility strategy (Step 2)
