# Profile Override Mechanism

How domains can override default profile skills.

---

## Overview

Profile skills handle the actual implementation/testing work during phase-5-execute. Unlike phase skills (which are system-only), profile skills CAN be overridden by domains.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROFILE SKILL RESOLUTION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Task with profile=implementation, domain=java                   │
│                         │                                        │
│                         ▼                                        │
│  resolve-workflow-skill --domain java --phase implementation     │
│                         │                                        │
│                         ▼                                        │
│  1. Check marshal.json: java.workflow_skills.implementation      │
│     → Found: pm-dev-java:java-implementation                     │
│                         │                                        │
│                         ▼                                        │
│  Return: { workflow_skill: pm-dev-java:java-implementation,      │
│            fallback: false }                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEM FALLBACK                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Task with profile=implementation, domain=generic                │
│                         │                                        │
│                         ▼                                        │
│  resolve-workflow-skill --domain generic --phase implementation  │
│                         │                                        │
│                         ▼                                        │
│  1. Check marshal.json: generic.workflow_skills.implementation   │
│     → Not found                                                  │
│                         │                                        │
│                         ▼                                        │
│  2. Fallback: system.workflow_skills.implementation              │
│     → pm-workflow:task-implementation                            │
│                         │                                        │
│                         ▼                                        │
│  Return: { workflow_skill: pm-workflow:task-implementation,      │
│            fallback: true }                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Profiles

| Profile | Purpose | System Default |
|---------|---------|----------------|
| `implementation` | Create/modify production code | `pm-workflow:task-implementation` |
| `module_testing` | Create/modify test code | `pm-workflow:task-module_testing` |

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
        "testing": "pm-dev-java:java-testing"
      }
    }
  }
}
```

---

## Resolution API

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --domain {domain} --phase {profile}
```

**Parameters**:
- `--domain`: Domain key from task (e.g., `java`, `javascript`)
- `--phase`: Profile from task (e.g., `implementation`, `module_testing`)

**Output**:
```toon
status: success
domain: {domain}
phase: {profile}
workflow_skill: {resolved skill reference}
fallback: {true if using system default}
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

## When to Override

| Scenario | Override? | Rationale |
|----------|-----------|-----------|
| Different coding patterns | Yes | Domain-specific idioms |
| Different testing framework | Yes | JUnit vs Jest vs pytest |
| Different verification commands | Yes | mvn vs npm vs cargo |
| Same generic workflow | No | System default works |
| Minor style differences | No | Handle via domain skills |

---

## Example: Java Implementation Override

```markdown
---
name: java-implementation
description: Java implementation profile with Maven patterns
allowed-tools: Read, Write, Edit, Bash, Skill
---

# Java Implementation

Profile skill for implementing Java code.

## Workflow

1. Read task via manage-tasks
2. Load task.skills (java-core, java-cdi, etc.)
3. Implement each step following Java patterns
4. Run mvn compile for verification
5. Track file changes
6. Return TOON output
```

---

## Related Documents

- [implementation.md](implementation.md) - Implementation profile contract
- [module_testing.md](module_testing.md) - Module testing profile contract
- [workflow-extension-api SKILL.md](../../SKILL.md) - Extension points overview
