# Module Testing Profile Contract

Workflow skill contract for module_testing profile - implements test creation tasks.

**System Default**: `pm-workflow:task-module_testing`

---

## Purpose

Testing profile skills:

1. Accept standardized input (plan_id, task_number)
2. Load domain skills from task.skills array
3. Create/modify test code following domain patterns
4. Track progress via manage-tasks
5. Track file changes for finalize phase
6. Return structured output

**Flow**: Task with pre-resolved skills → Test Implementation → File tracking → Verification

---

## When Used

Tasks with `profile: module_testing` are routed to module testing profile skills:

```toon
id: TASK-002
title: Add unit tests for UserService
domain: java
profile: module_testing
skills:
  - pm-dev-java:junit-core
  - pm-dev-java:cui-testing
deliverables: [2]
```

---

## Resolution

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --domain java --phase module_testing
```

**Result (domain override exists)**:
```toon
status: success
workflow_skill: pm-dev-java:java-module-testing
fallback: false
```

**Result (no domain override, system fallback)**:
```toon
status: success
workflow_skill: pm-workflow:task-module_testing
fallback: true
```

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task to execute |

---

## Skill Loading

Testing profile skills use two-tier skill loading:

| Tier | Source | Purpose |
|------|--------|---------|
| **Tier 1** | Agent frontmatter | System skills (architecture, rules) |
| **Tier 2** | `task.skills` array | Testing framework skills |

---

## Responsibilities

The testing workflow skill:

1. **Reads task**: Via manage-tasks get
2. **Loads testing skills**: From task.skills array
3. **Creates test files**: Following domain testing patterns
4. **Verifies tests pass**: Runs test command
5. **Tracks progress**: Via finalize-step
6. **Tracks file changes**: For finalize phase verification
7. **Returns structured output**: TOON status with summary

---

## Testing-Specific Concerns

| Aspect | Guidance |
|--------|----------|
| Test structure | Follow domain testing framework patterns (JUnit, Jest, etc.) |
| Test naming | Descriptive names following domain conventions |
| Assertions | Use domain-appropriate assertion libraries |
| Coverage | Track coverage if domain supports it |
| Isolation | Ensure tests are independent and repeatable |

---

## Return Structure

### Success Output

```toon
status: success
plan_id: {plan_id}
task_number: {task_number}

execution_summary:
  steps_completed: {N}
  steps_total: {M}
  files_modified[N]:
    - {test_path1}
    - {test_path2}

verification:
  passed: true
  command: "{test command used}"
  tests_passed: {count}

next_action: task_complete
```

### Error Output

```toon
status: error
plan_id: {plan_id}
task_number: {task_number}

execution_summary:
  steps_completed: {N}
  steps_failed: {M}

failure:
  step: {step_number}
  file: "{test file path}"
  error: "{error message}"
  recoverable: true|false

next_action: requires_attention
```

---

## Validation Rules

| Rule | Description |
|------|-------------|
| Input required | Both plan_id and task_number required |
| Status required | Output must include status field |
| Summary required | Output must include execution_summary |
| Tests must pass | Verification command must succeed |
| Files tracked | All test file modifications tracked |

---

## Related Documents

- [implementation.md](implementation.md) - Implementation profile contract
- [profile-mechanism.md](profile-mechanism.md) - How profile overrides work
- [task-contract.md](../../../manage-tasks/standards/task-contract.md) - Task structure
