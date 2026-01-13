# Task Execution Skill Contract

Workflow skill for execute phase - implements tasks using two-tier skill loading.

**Implementation**: `pm-workflow:phase-execute`

---

## Purpose

Task execution skills:

1. Accept standardized input (plan_id, task_number)
2. Resolve workflow skill based on domain and profile
3. Load domain skills from task.skills array (two-tier loading)
4. Iterate through steps
5. Track progress via manage-tasks
6. Track file changes for finalize phase
7. Return structured output

**Flow**: Task with pre-resolved skills → Implementation → File tracking → Verification

---

## Invocation

**Phase**: `execute`

**Agent invocation**:
```bash
plan-phase-agent plan_id={plan_id} phase=execute task_number={task_number}
```

**Skill resolution**:
```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --domain {task.domain} --phase {task.profile}
```

Result (domain override exists):
```toon
status: success
domain: java
phase: implementation
workflow_skill: pm-dev-java:java-implementation
fallback: false
```

Result (no domain override, system fallback):
```toon
status: success
domain: system
phase: implementation
workflow_skill: pm-workflow:phase-execute-implementation
fallback: true
```

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task to execute (e.g., 1 for TASK-001) |

---

## Two-Tier Skill Loading

See [pm-workflow-architecture:skill-loading](../../pm-workflow-architecture/standards/skill-loading.md) for complete visual diagrams.

| Tier | Source | Purpose | Loaded By |
|------|--------|---------|-----------|
| **Tier 1** | Agent frontmatter | System skills (architecture, rules) | Agent automatically |
| **Tier 2** | `task.skills` array | Domain-specific skills | Agent from task file |

### Example Task with Pre-Resolved Skills

```toon
id: TASK-001
title: Create CacheConfig class
domain: java
profile: implementation
skills:
  - pm-dev-java:java-core
  - pm-dev-java:java-cdi
deliverables: [1]
...
```

The `task-execute-agent` will:
1. Load system skills from its frontmatter (Tier 1)
2. Load `pm-dev-java:java-core` and `pm-dev-java:java-cdi` (Tier 2)

### Skills Pre-Resolved in Task

The `task.skills` array was populated during task-plan phase. Execute phase loads skills directly from the task without needing to call resolution APIs.

```
┌─────────────────────────────────────────────────────────────┐
│ Task Skill Loading (No Resolution Needed)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TASK-001.toon                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │ domain: java                                 │           │
│  │ profile: implementation                      │           │
│  │ skills:                                      │           │
│  │   - pm-dev-java:java-core      ← Pre-resolved│           │
│  │   - pm-dev-java:java-cdi       ← Pre-resolved│           │
│  └──────────────────────────────────────────────┘           │
│                         │                                   │
│                         ▼                                   │
│  Agent loads each skill directly                            │
│  (No resolve-domain-skills call needed)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Profile Mapping to Phase

The task's `profile` field maps to phase for workflow resolution:

| Task Profile | Resolve Phase | Description |
|--------------|---------------|-------------|
| `implementation` | `implementation` | Create/modify production code |
| `testing` | `testing` | Create/modify test code |
| `quality` | `quality` | Documentation, standards |

```bash
# Task with profile: implementation
resolve-workflow-skill --domain java --phase implementation

# Task with profile: testing
resolve-workflow-skill --domain java --phase testing
```

---

## System Fallback Behavior

When domain doesn't define a workflow skill override:

```
┌─────────────────────────────────────────────────────────────┐
│ Resolution with System Fallback                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  resolve-workflow-skill --domain generic --phase impl       │
│                         │                                   │
│                         ▼                                   │
│  1. Check: generic.workflow_skills.implementation           │
│     → Not found                                             │
│                         │                                   │
│                         ▼                                   │
│  2. Fallback: system.workflow_skills.implementation         │
│     → pm-workflow:phase-execute-implementation                       │
│                         │                                   │
│                         ▼                                   │
│  Return: { workflow_skill: pm-workflow:phase-execute-implementation, │
│            fallback: true }                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Skill Responsibilities

The workflow skill autonomously:

1. **Reads task**: Via manage-tasks get
2. **Loads domain skills**: From task.skills array (Tier 2)
3. **Iterates through steps**: Processing each file
4. **Tracks progress**: Via step-start/step-done
5. **Tracks file changes**: For finalize phase verification
6. **Returns structured output**: TOON status with summary

```
Execute Phase Workflow:
┌──────────────────────────────────────────────────────────────────┐
│ 1. Read task via manage-tasks get                                │
│ 2. Extract task.domain, task.profile, task.skills                │
│ 3. resolve-workflow-skill --domain X --phase {profile}           │
│    → Gets domain-specific OR system fallback workflow skill      │
│ 4. Load workflow skill                                           │
│ 5. Load each skill from task.skills array (Tier 2)               │
│ 6. Execute workflow skill's implementation process               │
│ 7. Track progress via manage-tasks step-start/step-done          │
│ 8. Track file changes via manage-references add-file             │
│ 9. Return structured TOON output                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Level

**Profile used**: From `task.profile` (implementation, testing, or quality)

Execute phase uses **full implementation knowledge**:
- All core patterns
- Implementation patterns (Builder, Factory, etc.)
- Annotations and their usage
- Testing patterns and frameworks
- Error handling and logging

---

## Script API Calls

### Task Retrieval

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get \
  --plan-id {plan_id} --number {task_number}
```

### Workflow Skill Resolution

```bash
# Uses task.domain and task.profile
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --domain java --phase implementation
```

### Skill Loading

For each skill in `task.skills`:
```
Skill: pm-dev-java:java-core
Skill: pm-dev-java:java-cdi
```

### Step Progress Tracking

```bash
# Start step
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks step-start \
  --plan-id {plan_id} --task {task_number} --step {step_number}

# Complete step
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks step-done \
  --plan-id {plan_id} --task {task_number} --step {step_number}
```

### File Change Tracking

**CRITICAL**: Execute phase MUST track file changes for finalize phase verification.

The finalize phase uses `scope: changed_only` to verify only files modified during execute. This requires execute to track all file changes in `references.toon`:

```bash
# After modifying a file, execute MUST call:
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-file \
    --plan-id {plan_id} --file {file_path}
```

**Consequences of missing tracking**:
- If `references.toon` is empty with `scope=changed_only`, finalize WARNS and falls back to `all`
- Full project scan is slower and may flag unrelated issues
- File tracking enables targeted verification

### Progress Logging

```bash
python3 .plan/execute-script.py plan-marshall:logging:manage-log \
  work {plan_id} INFO "[STEP] Completed step {N}: {file_path}"
```

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
    - {path1}
    - {path2}

verification:
  passed: true
  command: "{verification command used}"

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
  file: "{file path}"
  error: "{error message}"
  recoverable: true|false

next_action: requires_attention
```

---

## Output Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `success` or `error` |
| `plan_id` | string | Echo of input plan_id |
| `task_number` | number | Echo of input task_number |
| `execution_summary.steps_completed` | number | Steps successfully executed |
| `execution_summary.steps_total` | number | Total steps in task |
| `execution_summary.files_modified` | array | Paths of modified files |
| `verification.passed` | boolean | Whether verification succeeded |
| `verification.command` | string | Command used for verification |
| `failure.step` | number | Step number where failure occurred |
| `failure.error` | string | Error message |
| `failure.recoverable` | boolean | Whether retry might succeed |
| `next_action` | string | `task_complete` or `requires_attention` |

---

## Thin Agent Pattern

The `task-execute-agent` is a minimal wrapper:

```markdown
---
name: task-execute-agent
description: Execute single task with two-tier skill loading
tools: Read, Write, Edit, Bash, Skill
model: sonnet
skills: pm-workflow:task-execution, plan-marshall:general-development-rules
---

# Task Execute Agent

Thin agent that executes a single task. Loads workflow skill based on task.profile,
then loads task.skills array for domain knowledge.

## Step 0: Load System Skills (MANDATORY)

```
Skill: pm-workflow:task-execution
Skill: plan-marshall:general-development-rules
```

## Workflow

1. Read task via manage-tasks
2. Load workflow skill from resolve-workflow-skill
3. Load each skill from task.skills array
4. Execute skill's implement workflow
5. Track file changes via manage-references
6. Return structured TOON output
```

---

## Error Handling Requirements

### Skill Loading Failure

If skills fail to load:

```toon
status: error
error_type: skill_loading_failure
component: task-execute-agent
message: Failed to load skill: {skill_name}
failure:
  recoverable: false
next_action: requires_attention
```

### Step Execution Failure

If a step fails:

1. Log the error to work-log
2. Do NOT mark step as done
3. Return error status with failure details
4. Set `recoverable: true` if retry might help

### Verification Failure

If verification fails:

1. Log verification failure
2. Return error status
3. Include which command failed
4. Set `recoverable: true` (fix and retry)

---

## Validation Rules

| Rule | Description |
|------|-------------|
| Input required | Both plan_id and task_number required |
| Status required | Output must include status field |
| Summary required | Output must include execution_summary |
| Progress tracked | All step transitions logged |
| Files tracked | All file modifications tracked in references.toon |

---

## Integration

**Callers**:
- `plan-execute` skill → spawns task-execute-agent
- `/plan-execute` command → orchestrates execution

**Dependencies**:
- `manage-tasks` → task retrieval and progress tracking
- `manage-references` → file change tracking
- `manage-log` → work log entries

---

## Related Documents

- [task-plan-skill-contract.md](task-plan-skill-contract.md) - Previous phase (plan)
- [plan-finalize-skill-contract.md](plan-finalize-skill-contract.md) - Next phase (finalize)
- [task-contract.md](task-contract.md) - Task structure with domain, profile, skills
- [config-toon-format.md](../../manage-config/standards/config-toon-format.md) - Workflow skill configuration
