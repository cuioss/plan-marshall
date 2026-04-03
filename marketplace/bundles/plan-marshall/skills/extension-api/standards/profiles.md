# Profile Override Mechanism

Profile skills handle the actual implementation and testing work during phase-5-execute. Unlike phase skills (which are system-only), profile skills CAN be overridden by domains to apply domain-specific patterns, frameworks, and verification commands.

---

## Resolution Flow

Profile skill resolution checks for a domain-specific override first, then falls back to the system default.

```
┌─────────────────────────────────────────────────────────────┐
│                 PROFILE SKILL RESOLUTION                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Task with profile={profile}, domain={domain}                │
│                         │                                    │
│                         ▼                                    │
│  resolve-workflow-skill --domain {domain} --phase {profile}  │
│                         │                                    │
│                         ▼                                    │
│  1. Check marshal.json: {domain}.workflow_skills.{profile}   │
│     ┌── Found ──────────────────────────────────────┐        │
│     │ Return: workflow_skill={override}, fallback=false │     │
│     └───────────────────────────────────────────────┘        │
│     ┌── Not found ──────────────────────────────────┐        │
│     │ 2. Fallback: system.workflow_skills.{profile}  │        │
│     │ Return: workflow_skill={default}, fallback=true │       │
│     └───────────────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Profiles

| Profile | Purpose | System Default |
|---------|---------|----------------|
| `implementation` | Create/modify production code | `plan-marshall:task-executor` |
| `module_testing` | Create/modify test code | `plan-marshall:task-executor` |

---

## marshal.json Configuration

Domains configure profile overrides in marshal.json:

```json
{
  "skill_domains": {
    "java": {
      "domain": {
        "key": "java",
        "name": "Java",
        "description": "Java development with Maven/Gradle"
      },
      "workflow_skills": {
        "implementation": "pm-dev-java:java-implementation",
        "module_testing": "pm-dev-java:java-module-testing"
      }
    }
  }
}
```

---

## Resolution API

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill --domain {domain} --phase {profile}
```

**Parameters**:
- `--domain`: Domain key from task (e.g., `java`, `javascript`)
- `--phase`: Profile from task (e.g., `implementation`, `module_testing`)

**Output**:
```toon
status	success
domain	{domain}
phase	{profile}
workflow_skill	{resolved skill reference}
fallback	{true if using system default}
```

---

## Override Requirements

Domain-specific profile skills MUST:

1. **Accept same input** - plan_id and task_number
2. **Return same output structure** - status, execution_summary, etc.
3. **Use same APIs** - manage-tasks, manage-references, manage-log
4. **Track file changes** - For finalize phase verification

Domain-specific profile skills CAN:

1. **Load additional domain skills** - Beyond task.skills
2. **Use domain-specific verification** - Different commands
3. **Apply domain patterns** - Coding standards, idioms

---

## Implementation Profile Contract

**System Default**: `plan-marshall:task-executor`

**Purpose**: Task execution skills accept standardized input (plan_id, task_number), resolve the workflow skill based on domain and profile, load domain skills via two-tier loading, iterate through steps, track progress, and return structured output.

**Invocation**: Phase `5-execute` via `plan-phase-agent plan_id={plan_id} phase=5-execute task_number={task_number}`

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task to execute (e.g., 1 for TASK-001) |

### Two-Tier Skill Loading

| Tier | Source | Purpose | Loaded By |
|------|--------|---------|-----------|
| **Tier 1** | Agent frontmatter | System skills (architecture, rules) | Agent automatically |
| **Tier 2** | `task.skills` array | Domain-specific skills | Agent from task file |

The `task.skills` array is populated during the task-plan phase. Execute phase loads skills directly from the task without calling resolution APIs.

```
┌─────────────────────────────────────────────────────────────┐
│ Task Skill Loading (No Resolution Needed)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TASK-001.json                                               │
│  ┌──────────────────────────────────────────────┐            │
│  │ "domain": "java"                             │            │
│  │ "profile": "implementation"                  │            │
│  │ "skills": [                                  │            │
│  │   "pm-dev-java:java-core",     <- Pre-resolved│            │
│  │   "pm-dev-java:java-cdi"       <- Pre-resolved│            │
│  │ ]                                            │            │
│  └──────────────────────────────────────────────┘            │
│                         │                                    │
│                         ▼                                    │
│  Agent loads each skill directly                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Profile Mapping

| Task Profile | Resolve Phase | Description |
|--------------|---------------|-------------|
| `implementation` | `implementation` | Create/modify production code |
| `module_testing` | `module_testing` | Create/modify test code |
| `quality` | `quality` | Documentation, standards |

### Workflow Skill Responsibilities

The workflow skill autonomously:

1. **Reads task**: Via manage-tasks get
2. **Loads domain skills**: From task.skills array (Tier 2)
3. **Iterates through steps**: Processing each file
4. **Tracks progress**: Via finalize-step
5. **Tracks file changes**: For finalize phase verification
6. **Returns structured output**: TOON status with summary

### Return Structure

**Success**:
```toon
status	success
plan_id	{plan_id}
task_number	{task_number}

execution_summary:
  steps_completed: {N}
  steps_total: {M}
  files_modified[N]:
    - {path1}
    - {path2}

verification:
  passed: true
  command: "{verification command used}"

next_action	task_complete
```

**Error**:
```toon
status	error
plan_id	{plan_id}
task_number	{task_number}

execution_summary:
  steps_completed: {N}
  steps_failed: {M}

failure:
  step: {step_number}
  file: "{file path}"
  error: "{error message}"
  recoverable: true|false

next_action	requires_attention
```

### Validation Rules

| Rule | Description |
|------|-------------|
| Input required | Both plan_id and task_number required |
| Status required | Output must include status field |
| Summary required | Output must include execution_summary |
| Progress tracked | All step transitions logged |
| Files tracked | All file modifications tracked in references.json |

---

## Module Testing Profile Contract

**System Default**: `plan-marshall:task-executor`

**Purpose**: Testing profile skills create and modify test code following domain-specific testing patterns and frameworks.

### When Used

Tasks with `profile: module_testing` are routed to the module testing profile:

```toon
id	TASK-002
title	Add unit tests for UserService
domain	java
profile	module_testing
skills:
  - pm-dev-java:junit-core
  - pm-dev-java:cui-testing
deliverable	2
```

### Resolution Example

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill --domain java --phase module_testing
```

Domain override: `workflow_skill=pm-dev-java:java-module-testing, fallback=false`
System fallback: `workflow_skill=plan-marshall:task-executor, fallback=true`

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task to execute |

### Skill Loading

| Tier | Source | Purpose |
|------|--------|---------|
| **Tier 1** | Agent frontmatter | System skills (architecture, rules) |
| **Tier 2** | `task.skills` array | Testing framework skills |

### Responsibilities

The testing workflow skill:

1. **Reads task**: Via manage-tasks get
2. **Loads testing skills**: From task.skills array
3. **Creates test files**: Following domain testing patterns
4. **Verifies tests pass**: Runs test command
5. **Tracks progress**: Via finalize-step
6. **Tracks file changes**: For finalize phase verification
7. **Returns structured output**: TOON status with summary

### Testing-Specific Concerns

| Aspect | Guidance |
|--------|----------|
| Test structure | Follow domain testing framework patterns (JUnit, Jest, etc.) |
| Test naming | Descriptive names following domain conventions |
| Assertions | Use domain-appropriate assertion libraries |
| Coverage | Track coverage if domain supports it |
| Isolation | Ensure tests are independent and repeatable |

### Return Structure

**Success**:
```toon
status	success
plan_id	{plan_id}
task_number	{task_number}

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

next_action	task_complete
```

**Error**:
```toon
status	error
plan_id	{plan_id}
task_number	{task_number}

execution_summary:
  steps_completed: {N}
  steps_failed: {M}

failure:
  step: {step_number}
  file: "{test file path}"
  error: "{error message}"
  recoverable: true|false

next_action	requires_attention
```

### Validation Rules

| Rule | Description |
|------|-------------|
| Input required | Both plan_id and task_number required |
| Status required | Output must include status field |
| Summary required | Output must include execution_summary |
| Tests must pass | Verification command must succeed |
| Files tracked | All test file modifications tracked |

---

## When to Override

| Scenario | Override? | Rationale |
|----------|-----------|-----------|
| Different coding patterns | Yes | Domain-specific idioms |
| Different testing framework | Yes | JUnit vs Jest vs pytest |
| Different verification commands | Yes | mvn vs npm vs cargo |
| Same generic workflow | No | System default works |
| Minor style differences | No | Handle via domain skills |

---

## Related Documents

- [Extension API SKILL.md](../SKILL.md) - Extension points overview
- [skill-loading.md](../../ref-workflow-architecture/standards/skill-loading.md) - Two-tier skill loading diagrams
- [task-contract.md](../../manage-tasks/standards/task-contract.md) - Task structure with domain, profile, skills
