# Skill Domains Schema

JSON schema definition for the `skill_domains` section of marshal.json.

## Overview

The skill domains configuration uses a 5-phase workflow model with profile-based skill resolution. The `system` domain contains workflow skills, while technical domains (java, javascript, etc.) contain profile-based skills and optional workflow extensions.

## Schema Structure

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["bundle:skill"],
      "optionals": ["bundle:skill"],
      "workflow_skills": {
        "1-init": "pm-workflow:phase-1-init",
        "2-outline": "pm-workflow:phase-2-outline",
        "3-plan": "pm-workflow:phase-3-plan",
        "4-execute": "pm-workflow:phase-4-execute",
        "5-finalize": "pm-workflow:phase-5-finalize"
      },
      "task_executors": {
        "implementation": "pm-workflow:task-implementation",
        "module_testing": "pm-workflow:task-module_testing",
        "integration_testing": "pm-workflow:task-integration_testing"
      }
    },
    "{domain}": {
      "workflow_skill_extensions": {
        "outline": "bundle:extension-skill",
        "triage": "bundle:triage-skill"
      },
      "core": {
        "defaults": ["bundle:skill"],
        "optionals": ["bundle:skill"]
      },
      "implementation": { "defaults": [], "optionals": [] },
      "module_testing": { "defaults": [], "optionals": [] },
      "integration_testing": { "defaults": [], "optionals": [] },
      "quality": { "defaults": [], "optionals": [] }
    }
  }
}
```

## System Domain

The `system` domain is required and contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `defaults` | array | No | Base skills loaded for all tasks |
| `optionals` | array | No | Optional base skills available for selection |
| `workflow_skills` | object | Yes | Maps 5 phases to workflow skill references |
| `task_executors` | object | Yes | Maps profiles to task executor skills |

### Workflow Skills (5-Phase Model)

```json
{
  "workflow_skills": {
    "1-init": "pm-workflow:phase-1-init",
    "2-outline": "pm-workflow:phase-2-outline",
    "3-plan": "pm-workflow:phase-3-plan",
    "4-execute": "pm-workflow:phase-4-execute",
    "5-finalize": "pm-workflow:phase-5-finalize"
  }
}
```

| Phase | Purpose | Workflow Skill |
|-------|---------|----------------|
| `1-init` | Initialize plan, detect artifacts | `pm-workflow:phase-1-init` |
| `2-outline` | Create solution outline with deliverables | `pm-workflow:phase-2-outline` |
| `3-plan` | Transform deliverables into executable tasks | `pm-workflow:phase-3-plan` |
| `4-execute` | Execute individual tasks | `pm-workflow:phase-4-execute` |
| `5-finalize` | Verify, document, commit | `pm-workflow:phase-5-finalize` |

### Task Executors

Task executors map profile values to the workflow skill that executes tasks of that profile:

```json
{
  "task_executors": {
    "implementation": "pm-workflow:task-implementation",
    "module_testing": "pm-workflow:task-module_testing",
    "integration_testing": "pm-workflow:task-integration_testing"
  }
}
```

| Profile | Purpose | Default Executor |
|---------|---------|------------------|
| `implementation` | Production code tasks | `pm-workflow:task-implementation` |
| `module_testing` | Unit/module test tasks | `pm-workflow:task-module_testing` |
| `integration_testing` | Integration test tasks | `pm-workflow:task-integration_testing` |

**Extensibility**: The profile list is open for extension. To add a new profile:
1. Add profile key to `skills_by_profile` in domain `extension.py`
2. Create corresponding `pm-workflow:task-{profile}` skill
3. Marshall-steward auto-discovers and registers in `task_executors`

**Convention**: Profile `X` maps to skill `pm-workflow:task-X` by default.

## Technical Domains

Technical domains (java, javascript, etc.) use profile-based organization:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow_skill_extensions` | object | No | Domain-specific extensions for phases |
| `core` | object | Yes | Core skills loaded for all profiles |
| `implementation` | object | No | Skills for execute phase (production code) |
| `module_testing` | object | No | Skills for execute phase (unit/module tests) |
| `integration_testing` | object | No | Skills for execute phase (integration tests) |
| `quality` | object | No | Skills for finalize phase |

### Workflow Skill Extensions

Extensions provide domain-specific behavior without replacing workflow skills:

```json
{
  "workflow_skill_extensions": {
    "outline": "pm-dev-java:java-outline-ext",
    "triage": "pm-dev-java:ext-triage-java"
  }
}
```

| Type | Phase | Purpose |
|------|-------|---------|
| `outline` | outline | Domain-specific patterns for deliverable identification |
| `triage` | finalize | Domain-specific finding decision logic (fix/suppress/accept) |

### Profile Structure

Each profile contains defaults and optionals:

```json
{
  "{profile}": {
    "defaults": ["bundle:skill"],
    "optionals": ["bundle:skill"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `defaults` | array | Skills always loaded for this profile |
| `optionals` | array | Skills available for selection |

## Profile-to-Phase Mapping

| Profile | Phase | Use Case |
|---------|-------|----------|
| `implementation` | execute | Production code development tasks |
| `module_testing` | execute | Unit/module test development tasks |
| `integration_testing` | execute | Integration test development tasks |
| `quality` | finalize | Documentation, verification, compliance |

## Skill Resolution

### Task Executor Resolution

```bash
# Resolves profile to task executor skill from system.task_executors
plan-marshall-config resolve-task-executor --profile implementation
# Returns: pm-workflow:task-implementation

plan-marshall-config resolve-task-executor --profile module_testing
# Returns: pm-workflow:task-module_testing
```

### Workflow Skill Resolution

```bash
# Always resolves from system domain
plan-marshall-config resolve-workflow-skill --phase 2-outline
# Returns: pm-workflow:phase-2-outline
```

### Workflow Extension Resolution

```bash
# Returns extension or null if not defined
plan-marshall-config resolve-workflow-skill-extension --domain java --type outline
# Returns: pm-dev-java:java-outline-ext (or null)
```

### Domain Skills Resolution

```bash
# Returns core + profile skills
plan-marshall-config resolve-domain-skills --domain java --profile implementation
# Returns: java-core (from core.defaults) + java-cdi, java-maintenance (from implementation)
```

## Example: Java Domain

```json
{
  "java": {
    "workflow_skill_extensions": {
      "outline": "pm-dev-java:java-outline-ext",
      "triage": "pm-dev-java:ext-triage-java"
    },
    "core": {
      "defaults": ["pm-dev-java:java-core"],
      "optionals": ["pm-dev-java:java-null-safety", "pm-dev-java:java-lombok"]
    },
    "implementation": {
      "defaults": [],
      "optionals": ["pm-dev-java:java-cdi", "pm-dev-java:java-maintenance"]
    },
    "module_testing": {
      "defaults": ["pm-dev-java:junit-core"],
      "optionals": []
    },
    "integration_testing": {
      "defaults": ["pm-dev-java:junit-core"],
      "optionals": ["pm-dev-java:junit-integration"]
    },
    "quality": {
      "defaults": ["pm-dev-java:javadoc"],
      "optionals": []
    }
  }
}
```

## Example: JavaScript Domain

```json
{
  "javascript": {
    "workflow_skill_extensions": {
      "outline": "pm-dev-frontend:js-outline-ext"
    },
    "core": {
      "defaults": ["pm-dev-frontend:cui-javascript"],
      "optionals": ["pm-dev-frontend:cui-jsdoc", "pm-dev-frontend:cui-javascript-project"]
    },
    "implementation": {
      "defaults": [],
      "optionals": ["pm-dev-frontend:cui-javascript-linting", "pm-dev-frontend:cui-javascript-maintenance"]
    },
    "module_testing": {
      "defaults": ["pm-dev-frontend:cui-javascript-unit-testing"],
      "optionals": []
    },
    "integration_testing": {
      "defaults": [],
      "optionals": ["pm-dev-frontend:cui-cypress"]
    },
    "quality": {
      "defaults": [],
      "optionals": []
    }
  }
}
```

## Validation Rules

1. **System domain required**: `skill_domains.system` must exist
2. **Workflow skills required**: `system.workflow_skills` must have all 5 phases
3. **Task executors required**: `system.task_executors` must exist with at least `implementation`
4. **Profile structure**: If domain has profiles, must have at least `core`
5. **Extension types**: Only `outline` and `triage` are valid extension types
6. **Skill format**: All skills must be `bundle:skill` format

## Reserved Keys

These keys are reserved in domain configuration and cannot be used as profile names:

- `workflow_skills` - System domain only
- `task_executors` - System domain only
- `workflow_skill_extensions` - Domain extensions
- `core` - Core skills for all profiles
- `defaults` - Top-level defaults (flat structure compatibility)
- `optionals` - Top-level optionals (flat structure compatibility)
