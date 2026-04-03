---
name: task-implementation
description: Domain-agnostic implementation task execution with two-tier skill loading
user-invocable: false
---

# Task Implementation Skill

**Role**: Domain-agnostic workflow skill for executing implementation tasks (profile=implementation). Loaded by `plan-marshall:phase-5-execute` skill when `task.profile` is `implementation`.

**Key Pattern**: Agent loads this skill via `resolve-task-executor --profile implementation`. Skill executes a generic workflow: understand context → plan → implement → verify. Domain-specific knowledge comes from `task.skills` (loaded by agent).

## Contract Compliance

**MANDATORY**: Follow the contracts defined in:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Contract | `plan-marshall:manage-tasks/standards/task-contract.md` | Task structure, fields, status values, and JSON schema |
| Task Executor Base | `plan-marshall:ref-workflow-architecture/standards/task-executor-base.md` | Shared workflow steps for all task executors |

## Two-Tier Skill Loading

See [ref-workflow-architecture:skill-loading](../ref-workflow-architecture/standards/skill-loading.md) for the complete two-tier skill loading pattern. Agent loads Tier 1 (system skills) automatically, then Tier 2 (domain skills from `task.skills`). This workflow skill defines HOW the agent executes.

## Input / Output

See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for the common input contract and base output schema. This profile uses the base output contract without additional fields.

## Workflow

This skill follows the shared task executor workflow. Steps marked **[BASE]** are defined in [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) — follow them exactly. Steps without the tag are implementation-specific.

### Step 1: Load Task Context [BASE]

Follow the base workflow. Verify `profile` is `implementation`.

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

### Step 7: Run Verification [BASE]

Implementation tasks verify compilability only — full test execution belongs to module_testing profile. The safety net resolve command is `compile`.

### Step 8: Handle Verification Results [BASE]

On failure: analyze error output, identify failing component, fix the issue, re-run verification.

### Step 9: Record Lessons [BASE]

Use component `"plan-marshall:task-implementation"`.

### Step 10: Return Results [BASE]

## Error Handling

See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for common error handling (missing dependencies, verification timeout).

### Conflicting Changes

If changes conflict with existing code:
- Analyze conflict
- Prefer preserving existing behavior
- Ask for clarification if needed

## Integration

**Invoked by**: `plan-marshall:phase-5-execute` skill (when task.profile = implementation)

**Skill Loading**: Agent loads this skill via `resolve-task-executor --profile implementation`

**Script Notations**: See [task-executor-base.md](../ref-workflow-architecture/standards/task-executor-base.md) for the complete list. This profile additionally uses:
- `plan-marshall:manage-config:manage-config` — Read compatibility from project config
