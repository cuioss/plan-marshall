# Execute-Task Skills

How tasks are routed to the appropriate execute-task skill and the shared workflow that all execute-task skills follow.

---

## Routing Overview

Execute-task skills are workflow skills that handle the actual implementation or testing work during task execution. Unlike phase skills (which are system-only), execute-task skills are configured via marshal.json and can be extended.

**Key Design**: Profile determines execution skill; domain determines knowledge skills.

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK EXECUTION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TASK-001.json                                                   │
│  ├─ profile: implementation     ←─ Determines execute-task skill │
│  ├─ domain: java                ←─ (informational only)          │
│  └─ skills: [java-core, ...]    ←─ Domain knowledge skills       │
│                                                                  │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  resolve-execute-task-skill --profile implementation             │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  marshal.json: skill_domains.system.execute_task_skills          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ "execute_task_skills": {                                    │ │
│  │   "implementation": "plan-marshall:execute-task",           │ │
│  │   "module_testing": "plan-marshall:execute-task"            │ │
│  │ }                                                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  Skill: plan-marshall:execute-task         ←─ Execute-task skill │
│  Skill: pm-dev-java:java-core              ←─ Domain skills      │
│  Skill: pm-dev-java:java-cdi               ←─ from task.skills   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Profile Naming Conventions

**Canonical profile names use underscores** (not hyphens):

| Profile | Purpose | Default Execute-Task Skill |
|---------|---------|---------------------------|
| `implementation` | Production code creation/modification | `plan-marshall:execute-task` |
| `module_testing` | Unit/module test creation | `plan-marshall:execute-task` |
| `verification` | Run commands without modifying files | `plan-marshall:execute-task` |

**Why underscores?** Profiles are used as JSON keys, TOON field values, and CLI parameters — underscores are more consistent with these conventions.

---

## Resolve API

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-execute-task-skill --profile {profile}
```

**Output**:
```toon
status: success
profile: implementation
execute_task_skill: plan-marshall:execute-task
```

**Error (unknown profile)**:
```toon
status: error
error: Unknown profile 'X'. Available profiles: implementation, module_testing
```

---

## marshal.json Configuration

Execute-task skills are configured in the system domain:

```json
{
  "skill_domains": {
    "system": {
      "workflow_skills": { ... },
      "execute_task_skills": {
        "implementation": "plan-marshall:execute-task",
        "module_testing": "plan-marshall:execute-task",
        "verification": "plan-marshall:execute-task"
      }
    }
  }
}
```

**Convention**: All profiles map to `plan-marshall:execute-task` by default. The skill handles profile dispatch internally.

---

## Automatic Configuration

Marshall-steward auto-populates execute_task_skills during setup:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  configure-execute-task-skills
```

**Discovery Process**:
1. Scans all configured domains in marshal.json
2. Extracts profile keys from each domain (excluding reserved keys like `core`, `workflow_skills`)
3. Includes DEFAULT_PROFILES from `_config_defaults.py`
4. Maps each profile to `plan-marshall:execute-task`
5. Persists to `skill_domains.system.execute_task_skills`

---

## Extensibility

The profile system is open for extension. While `_config_defaults.py` defines a set of default profiles (`implementation`, `module_testing`, `integration_testing`, `verification`), new profiles can be added without modifying core workflow code.

### Steps to Add a New Profile

1. **Add profile to domain extension.py**:
   ```python
   def get_skill_domains(self) -> list[dict]:
       return [{
           "domain": {...},
           "profiles": {
               "core": {...},
               "implementation": {...},
               "module_testing": {...},
               "my_new_profile": {  # New profile
                   "defaults": ["my-bundle:my-skill"],
                   "optionals": []
               }
           }
       }]
   ```

2. **Create corresponding execute-task skill**:
   ```
   marketplace/bundles/plan-marshall/skills/execute-my_new_profile/
   └── SKILL.md  # Defines execution workflow for this profile
   ```

3. **Run marshall-steward to auto-discover**:
   ```bash
   /marshall-steward
   ```

4. **Verify configuration**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     resolve-execute-task-skill --profile my_new_profile
   ```

---

## Data Flow

For the complete architecture → outline → plan → execute skill resolution flow, see [skill-loading.md](skill-loading.md).

---

## Verification Scope by Profile

| Profile | Verification Command | Scope |
|---------|---------------------|-------|
| `implementation` | `compile` | Compilability only — full tests belong to module_testing |
| `module_testing` | `module-tests` | Full test suite for the module |
| `verification` | (from task steps) | Run step commands without modifying files |

---

## Shared Execute-Task Workflow

The unified `plan-marshall:execute-task` skill handles all profiles. Common workflow steps are shared, with profile-specific behavior documented per profile section in the skill.

### Common Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task number to execute |

---

### Load Task Context

Read the task file to understand what needs to be done:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \
  --plan-id {plan_id} \
  --task-number {task_number}
```

Extract key fields:
- `domain`: Domain for this task
- `profile`: Should match the expected profile for this executor
- `skills`: Domain skills to apply (already loaded by agent)
- `description`: What to do
- `steps`: File paths (or commands for verification profile) to work on
- `verification`: How to verify success
- `depends_on`: Dependencies (should be complete)

**Note**: Steps are executed sequentially. No explicit "in_progress" marker is needed — proceed directly to execution.

---

### Mark Step Complete

After completing each step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --step {N} \
  --outcome done
```

---

### Run Verification

After all steps complete, run task verification.

Execute the verification commands from `task.verification.commands`. Every task SHOULD have commands populated by the plan phase (copied from the deliverable).

**Safety net** (should not trigger in normal operation): If verification commands are missing, log a WARNING and resolve from architecture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[VERIFY] ({skill_name}) TASK-{N} missing verification — falling back to architecture resolve"

python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command {resolve_command} --module {module} \
  --trace-plan-id {plan_id}
```

Where `{resolve_command}` depends on the profile:
- `implementation` → `compile`
- `module_testing` → `module-tests`

---

### Handle Verification Results

**If verification passes**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --status done
```

**If verification fails**:

1. Analyze error output
2. Identify failing component
3. Fix the issue (profile-specific — see executor skill for scope)
4. Re-run verification
5. Iterate until pass (max `verification_max_iterations` from config, default 5)

If still failing after max iterations:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --status blocked
```

Record details in work.log using manage-log.

---

### Record Lessons

On issues or unexpected patterns, use the two-step path-allocate flow:

1. Allocate a lesson file and capture the returned `path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{skill_notation}" \
  --category improvement \
  --title "{issue summary}"
```

2. Parse `path` from the output and write the lesson body directly to that path via the Write tool. This keeps the markdown body — including `##` sections, code fences, and multiple paragraphs — out of shell argument space.

**Valid categories**: `bug`, `improvement`, `anti-pattern`

---

### Return Results

Base output contract (profile-specific executors may add additional fields):

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

## Common Error Handling

### Missing Dependency

If a file depends on code not yet implemented:
- Check if dependency is in a later step
- If yes, reorder steps
- If no, create minimal stub and note

### Verification Timeout

If verification command hangs:
- Kill after 5 minutes
- Record timeout in lessons
- Try with reduced scope

---

## Common Script Notations

All execute-task skills use these notations (use EXACTLY as shown):

| Notation | Purpose |
|----------|---------|
| `plan-marshall:manage-tasks:manage-tasks` | Task operations (read, update, finalize-step) |
| `plan-marshall:manage-lessons:manage-lessons` | Record lessons (add) |
| `plan-marshall:manage-logging:manage-logging` | Logging (work) |
| `plan-marshall:manage-config:manage-config` | Read project configuration |
| `plan-marshall:manage-architecture:architecture` | Build command resolution (verification fallback) |

---

## Related

- [skill-loading.md](skill-loading.md) — Two-tier skill loading
- [phases.md](phases.md) — Workflow phase definitions
