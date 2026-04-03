# Task Executors

How tasks are routed to the appropriate task executor skill and the shared workflow that all executors follow.

---

## Routing Overview

Task executors are workflow skills that handle the actual implementation or testing work during task execution. Unlike phase skills (which are system-only), task executors are configured via marshal.json and can be extended.

**Key Design**: Profile determines execution skill; domain determines knowledge skills.

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK EXECUTION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TASK-001.json                                                   │
│  ├─ profile: implementation     ←─ Determines task executor      │
│  ├─ domain: java                ←─ (informational only)          │
│  └─ skills: [java-core, ...]    ←─ Domain knowledge skills       │
│                                                                  │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  resolve-task-executor --profile implementation                  │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  marshal.json: skill_domains.system.task_executors               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ "task_executors": {                                         │ │
│  │   "implementation": "plan-marshall:task-implementation",      │ │
│  │   "module_testing": "plan-marshall:task-module-testing"       │ │
│  │ }                                                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  Skill: plan-marshall:task-implementation    ←─ Task executor      │
│  Skill: pm-dev-java:java-core              ←─ Domain skills      │
│  Skill: pm-dev-java:java-cdi               ←─ from task.skills   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Profile Naming Conventions

**Canonical profile names use underscores** (not hyphens):

| Profile | Purpose | Default Task Executor |
|---------|---------|----------------------|
| `implementation` | Production code creation/modification | `plan-marshall:task-implementation` |
| `module_testing` | Unit/module test creation | `plan-marshall:task-module-testing` |
| `verification` | Run commands without modifying files | `plan-marshall:task-verification` |

**Why underscores?** Profiles are used as JSON keys, TOON field values, and CLI parameters — underscores are more consistent with these conventions.

---

## Resolve API

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-task-executor --profile {profile}
```

**Output**:
```toon
status: success
profile: implementation
task_executor: plan-marshall:task-implementation
```

**Error (unknown profile)**:
```toon
status: error
error: Unknown profile 'X'. Available profiles: implementation, module_testing
```

---

## marshal.json Configuration

Task executors are configured in the system domain:

```json
{
  "skill_domains": {
    "system": {
      "workflow_skills": { ... },
      "task_executors": {
        "implementation": "plan-marshall:task-implementation",
        "module_testing": "plan-marshall:task-module-testing"
      }
    }
  }
}
```

**Convention**: Profile `X` maps to skill `plan-marshall:task-X` by default.

---

## Automatic Configuration

Marshall-steward auto-populates task_executors during setup:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  configure-task-executors
```

**Discovery Process**:
1. Scans all configured domains in marshal.json
2. Extracts profile keys from each domain (excluding reserved keys like `core`, `workflow_skills`)
3. Includes DEFAULT_PROFILES from `_config_defaults.py`
4. Maps each profile to `plan-marshall:task-{profile}`
5. Persists to `skill_domains.system.task_executors`

---

## Extensibility

**There is NO finite or hardcoded list of profiles.**

The profile system is designed for extension. New profiles can be added without modifying core workflow code.

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

2. **Create corresponding task executor skill**:
   ```
   marketplace/bundles/plan-marshall/skills/task-my_new_profile/
   └── SKILL.md  # Defines execution workflow for this profile
   ```

3. **Run marshall-steward to auto-discover**:
   ```bash
   /marshall-steward
   ```

4. **Verify configuration**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     resolve-task-executor --profile my_new_profile
   ```

---

## Data Flow Summary

```
Architecture Analysis
       │
       ▼
module.skills_by_profile = {
  "implementation": [java-core, java-cdi],
  "module_testing": [java-core, junit-core]
}
       │
       ▼
Phase-3-Outline
       │
       ▼
deliverable.profiles = [implementation, module_testing]
       │
       ▼ (create task per profile, resolve skills from architecture)
Phase-4-Plan
       │
       ▼
TASK-001.json
  profile: implementation
  skills: [java-core, java-cdi]
       │
       ▼
Phase-5-Execute
       │
       ▼
resolve-task-executor --profile implementation
       │
       ▼
Skill: plan-marshall:task-implementation  (executes task)
Skill: pm-dev-java:java-core           (domain knowledge)
Skill: pm-dev-java:java-cdi            (domain knowledge)
```

---

## Shared Executor Workflow

All task executor skills (task-implementation, task-module-testing, task-verification) share a common workflow. Profile-specific skills define their unique steps and reference this section for the common steps.

### Common Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task number to execute |

---

### Load Task Context

Read the task file to understand what needs to be done:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get \
  --plan-id {plan_id} \
  --number {task_number}
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
  --task {task_number} \
  --step {N} \
  --outcome done
```

---

### Run Verification

After all steps complete, run task verification.

Execute the verification commands from `task.verification.commands`. Every task SHOULD have commands populated by the plan phase (copied from the deliverable).

**Safety net** (should not trigger in normal operation): If verification commands are missing, log a WARN and resolve from architecture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN --message "[VERIFY] ({skill_name}) TASK-{N} missing verification — falling back to architecture resolve"

python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command {resolve_command} --name {module} \
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
  --number {task_number} \
  --status done
```

**If verification fails**:

1. Analyze error output
2. Identify failing component
3. Fix the issue (profile-specific — see executor skill for scope)
4. Re-run verification
5. Iterate until pass (max 3 iterations)

If still failing after 3 iterations:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --number {task_number} \
  --status blocked
```

Record details in work.log using manage-log.

---

### Record Lessons

On issues or unexpected patterns:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{skill_notation}" \
  --category improvement \
  --title "{issue summary}" \
  --detail "{context and resolution}"
```

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

All task executor skills use these notations (use EXACTLY as shown):

| Notation | Purpose |
|----------|---------|
| `plan-marshall:manage-tasks:manage-tasks` | Task operations (get, update, finalize-step) |
| `plan-marshall:manage-lessons:manage-lessons` | Record lessons (add) |
| `plan-marshall:manage-logging:manage-logging` | Logging (work) |
| `plan-marshall:manage-config:manage-config` | Read project configuration |
| `plan-marshall:manage-architecture:architecture` | Build command resolution (verification fallback) |

---

## Related Documents

- [skill-loading.md](skill-loading.md) - Two-tier skill loading pattern
- [phases.md](phases.md) - Workflow phase definitions
- [agents.md](agents.md) - Agent responsibilities including phase-5-execute skill
- `plan-marshall:extension-api` - Extension points
