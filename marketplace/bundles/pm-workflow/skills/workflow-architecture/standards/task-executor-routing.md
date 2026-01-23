# Task Executor Routing

How tasks are routed to the appropriate task executor skill during phase-5-execute.

---

## Overview

Task executors are workflow skills that handle the actual implementation or testing work during task execution. Unlike phase skills (which are system-only), task executors are configured via marshal.json and can be extended.

**Key Design**: Profile determines execution skill; domain determines knowledge skills.

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK EXECUTION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TASK-001.toon                                                   │
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
│  │   "implementation": "pm-workflow:task-implementation",      │ │
│  │   "module_testing": "pm-workflow:task-module_testing",      │ │
│  │   "integration_testing": "pm-workflow:task-integration_testing" │
│  │ }                                                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  Returns: pm-workflow:task-implementation                        │
│                                                                  │
│                    │                                             │
│                    ▼                                             │
│                                                                  │
│  Skill: pm-workflow:task-implementation    ←─ Task executor      │
│  Skill: pm-dev-java:java-core              ←─ Domain skills      │
│  Skill: pm-dev-java:java-cdi               ←─ from task.skills   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
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
        "implementation": "pm-workflow:task-implementation",
        "module_testing": "pm-workflow:task-module_testing",
        "integration_testing": "pm-workflow:task-integration_testing"
      }
    }
  }
}
```

**Convention**: Profile `X` maps to skill `pm-workflow:task-X` by default.

---

## API Reference

### resolve-task-executor

Resolve task executor skill for a given profile.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-task-executor --profile {profile}
```

**Parameters**:
- `--profile`: Profile name from task (e.g., `implementation`, `module_testing`)

**Output**:
```toon
status: success
profile: implementation
task_executor: pm-workflow:task-implementation
```

**Error (unknown profile)**:
```toon
status: error
error: Unknown profile 'X'. Available profiles: implementation, module_testing, integration_testing
```

---

## Profile Naming Conventions

**Canonical profile names use underscores** (not hyphens):

| Profile | Purpose | Default Task Executor |
|---------|---------|----------------------|
| `implementation` | Production code creation/modification | `pm-workflow:task-implementation` |
| `module_testing` | Unit/module test creation | `pm-workflow:task-module_testing` |
| `integration_testing` | Integration test creation | `pm-workflow:task-integration_testing` |

**Why underscores?** Profiles are used as:
1. Keys in `skills_by_profile` JSON objects
2. Field values in TOON task files
3. Parameters to `resolve-task-executor`

Underscores are more consistent with JSON key conventions.

---

## Automatic Configuration

Marshall-steward auto-populates task_executors during setup:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  configure-task-executors
```

**Discovery Process**:
1. Scans all configured domains in marshal.json
2. Extracts profile keys from each domain (excluding reserved keys like `core`, `workflow_skills`)
3. Includes DEFAULT_PROFILES from `_config_defaults.py`
4. Maps each profile to `pm-workflow:task-{profile}`
5. Persists to `skill_domains.system.task_executors`

---

## Extensibility

**There is NO finite or hardcoded list of profiles.**

The profile system is designed for extension. New profiles can be added without modifying core workflow code.

### Steps to Add a New Profile

1. **Add profile to domain extension.py**:
   ```python
   def get_skill_domains(self) -> dict:
       return {
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
       }
   ```

2. **Create corresponding task executor skill**:
   ```
   marketplace/bundles/pm-workflow/skills/task-my_new_profile/
   └── SKILL.md  # Defines execution workflow for this profile
   ```

3. **Run marshall-steward to auto-discover**:
   ```bash
   /marshall-steward
   ```
   The `configure-task-executors` step automatically discovers the new profile from extension.py and registers it in marshal.json.

4. **Verify configuration**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
     resolve-task-executor --profile my_new_profile
   ```

### Example: Documentation Profile

The `documentation` profile demonstrates this pattern:

1. **pm-documents extension.py** defines `documentation` profile with AsciiDoc skills
2. **task-documentation** skill (if created) would handle documentation tasks
3. Deliverables with `profile: documentation` route to this executor
4. Domain skills provide AsciiDoc/ADR patterns

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
TASK-001.toon
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
Skill: pm-workflow:task-implementation  (executes task)
Skill: pm-dev-java:java-core           (domain knowledge)
Skill: pm-dev-java:java-cdi            (domain knowledge)
```

---

## Related Documents

- [skill-loading.md](skill-loading.md) - Two-tier skill loading pattern
- [phases.md](phases.md) - Workflow phase definitions
- [agents.md](agents.md) - Agent responsibilities including task-execute-agent
- [profile-mechanism.md](../workflow-extension-api/standards/profiles/profile-mechanism.md) - Profile override mechanism
