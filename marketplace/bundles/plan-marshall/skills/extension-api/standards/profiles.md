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

These are the profiles defined in `ExtensionBase.APPLICABLE_PROFILES`. Extensions declare skills per profile in `get_skill_domains()`. The `core` profile is special — it's always merged into other profiles and not listed here.

| Profile | Purpose | System Default | Detection |
|---------|---------|----------------|-----------|
| `implementation` | Create/modify production code | `plan-marshall:task-executor` | Always included |
| `module_testing` | Create/modify test code | `plan-marshall:task-executor` | Always included |
| `integration_testing` | Integration tests (containers, external services) | `plan-marshall:task-executor` | Signal-based (e.g., Failsafe plugin, testcontainers deps) |
| `quality` | Documentation standards, code quality | `plan-marshall:task-executor` | Always included |
| `documentation` | Documentation-specific tasks (AsciiDoc, ADRs) | `plan-marshall:task-executor` | Signal-based (module has `doc/*.adoc` files) |

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

**Error handling**: If a profile skill reference in marshal.json points to a non-existent skill, resolution falls back to the system default (`plan-marshall:task-executor`) with `fallback=true`. The invalid reference is logged as a warning.

---

## Profile Execution Contract

All profiles share the same execution contract. The system default for all profiles is `plan-marshall:task-executor`.

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

### Profile Mapping

| Task Profile | Description |
|--------------|-------------|
| `implementation` | Create/modify production code |
| `module_testing` | Create/modify test code |
| `integration_testing` | Create/modify integration tests |
| `quality` | Documentation, code quality standards |
| `documentation` | Documentation-specific tasks |

### Workflow Skill Responsibilities

The workflow skill autonomously:

1. **Reads task**: Via manage-tasks get
2. **Loads domain skills**: From task.skills array (Tier 2)
3. **Iterates through steps**: Processing each file
4. **Tracks progress**: Via finalize-step
5. **Tracks file changes**: For finalize phase verification
6. **Returns structured output**: TOON status with summary

### Profile-Specific Concerns

| Profile | Additional Responsibilities |
|---------|---------------------------|
| `implementation` | Follow domain coding patterns and standards |
| `module_testing` | Follow domain test framework patterns; verify tests pass; track coverage |
| `integration_testing` | Manage external service dependencies; use domain IT patterns |
| `quality` | Apply documentation and quality standards |
| `documentation` | Follow AsciiDoc/documentation formatting standards |

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

- [Extension API SKILL.md](../SKILL.md) — Extension points overview
- [extension-contract.md](extension-contract.md) — ExtensionBase contract with profile definitions
- [workflow-overview.md](workflow-overview.md) — 6-phase workflow and phase transitions
