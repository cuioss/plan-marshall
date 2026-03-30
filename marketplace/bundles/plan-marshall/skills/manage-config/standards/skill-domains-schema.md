# Skill Domains Schema

JSON schema definition for the `skill_domains` section of marshal.json.

## Overview

The skill domains configuration uses a 6-phase workflow model with profile-based skill resolution. The `system` domain contains workflow skills, while technical domains (java, javascript, etc.) contain profile-based skills and optional workflow extensions.

## Schema Structure

```json
{
  "skill_domains": {
    "active_profiles": ["implementation", "module_testing", "quality"],
    "system": {
      "defaults": ["bundle:skill"],
      "optionals": ["bundle:skill"],
      "workflow_skills": {
        "1-init": "plan-marshall:phase-1-init",
        "2-refine": "plan-marshall:phase-2-refine",
        "3-outline": "plan-marshall:phase-3-outline",
        "4-plan": "plan-marshall:phase-4-plan",
        "5-execute": "plan-marshall:phase-5-execute",
        "6-finalize": "plan-marshall:phase-6-finalize"
      },
      "task_executors": {
        "implementation": "plan-marshall:task-implementation",
        "module_testing": "plan-marshall:task-module-testing",
        "integration_testing": "plan-marshall:task-integration_testing"
      }
    },
    "{domain}": {
      "active_profiles": ["implementation", "module_testing"],
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
| `workflow_skills` | object | Yes | Maps 6 phases to workflow skill references |
| `task_executors` | object | Yes | Maps profiles to task executor skills |

### Workflow Skills (6-Phase Model)

```json
{
  "workflow_skills": {
    "1-init": "plan-marshall:phase-1-init",
    "2-refine": "plan-marshall:phase-2-refine",
    "3-outline": "plan-marshall:phase-3-outline",
    "4-plan": "plan-marshall:phase-4-plan",
    "5-execute": "plan-marshall:phase-5-execute",
    "6-finalize": "plan-marshall:phase-6-finalize"
  }
}
```

| Phase | Purpose | Workflow Skill |
|-------|---------|----------------|
| `1-init` | Initialize plan, detect artifacts | `plan-marshall:phase-1-init` |
| `2-refine` | Clarify request until confidence threshold | `plan-marshall:phase-2-refine` |
| `3-outline` | Create solution outline with deliverables | `plan-marshall:phase-3-outline` |
| `4-plan` | Transform deliverables into executable tasks | `plan-marshall:phase-4-plan` |
| `5-execute` | Execute individual tasks + verification | `plan-marshall:phase-5-execute` |
| `6-finalize` | Commit, push, PR creation | `plan-marshall:phase-6-finalize` |

### Task Executors

Task executors map profile values to the workflow skill that executes tasks of that profile:

```json
{
  "task_executors": {
    "implementation": "plan-marshall:task-implementation",
    "module_testing": "plan-marshall:task-module-testing",
    "integration_testing": "plan-marshall:task-integration_testing"
  }
}
```

| Profile | Purpose | Default Executor |
|---------|---------|------------------|
| `implementation` | Production code tasks | `plan-marshall:task-implementation` |
| `module_testing` | Unit/module test tasks | `plan-marshall:task-module-testing` |
| `integration_testing` | Integration test tasks | `plan-marshall:task-integration_testing` |

**Extensibility**: The profile list is open for extension. To add a new profile:
1. Add profile key to `skills_by_profile` in domain `extension.py`
2. Create corresponding `plan-marshall:task-{profile}` skill
3. Marshall-steward auto-discovers and registers in `task_executors`

**Convention**: Profile `X` maps to skill `plan-marshall:task-X` by default.

## Technical Domains

Technical domains (java, javascript, etc.) use profile-based organization:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow_skill_extensions` | object | No | Domain-specific extensions for phases |
| `core` | object | Yes | Core skills loaded for all profiles |
| `implementation` | object | No | Skills for execute phase (production code) |
| `module_testing` | object | No | Skills for execute phase (unit/module tests) |
| `integration_testing` | object | No | Skills for execute phase (integration tests) |
| `quality` | object | No | Skills for verify phase |

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
| `triage` | execute (verification), finalize | Domain-specific finding decision logic (fix/suppress/accept) |

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
| `quality` | verify | Documentation, verification, compliance |

## Skill Resolution

### Task Executor Resolution

```bash
# Resolves profile to task executor skill from system.task_executors
manage-config resolve-task-executor --profile implementation
# Returns: plan-marshall:task-implementation

manage-config resolve-task-executor --profile module_testing
# Returns: plan-marshall:task-module-testing
```

### Workflow Skill Resolution

```bash
# Always resolves from system domain
manage-config resolve-workflow-skill --phase 3-outline
# Returns: plan-marshall:phase-3-outline
```

### Workflow Extension Resolution

```bash
# Returns extension or null if not defined
manage-config resolve-workflow-skill-extension --domain java --type outline
# Returns: pm-dev-java:java-outline-ext (or null)
```

### Domain Skills Resolution

```bash
# Returns core + profile skills
manage-config resolve-domain-skills --domain java --profile implementation
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
      "defaults": ["pm-dev-frontend:javascript"],
      "optionals": []
    },
    "implementation": {
      "defaults": [],
      "optionals": ["pm-dev-frontend:js-enforce-eslint"]
    },
    "module_testing": {
      "defaults": [],
      "optionals": []
    },
    "quality": {
      "defaults": [],
      "optionals": []
    }
  }
}
```

## Active Profiles (Profile Filtering)

Controls which profiles are emitted during architecture enrichment and skill resolution.

### Three-Layer Resolution

| Layer | Source | Scope | Description |
|-------|--------|-------|-------------|
| 1 | Extension signal detection | Per-module | `_detect_applicable_profiles()` inspects module signals |
| 2 | `skill_domains.active_profiles` | Global | Positive list overrides detection for all modules |
| 2b | `skill_domains.{domain}.active_profiles` | Per-domain | Overrides global for specific domain |
| 3 | `--profiles` flag on `enrich add-domain` | Per-module | Explicit per-module override at enrichment time |

**Resolution order**: `--profiles flag` > `per-domain active_profiles` > `global active_profiles` > `signal detection` > `all defined profiles`

### Global Active Profiles

```json
{
  "skill_domains": {
    "active_profiles": ["implementation", "module_testing", "quality"]
  }
}
```

When set, only these profiles are emitted for all domains. Profiles not in the list (e.g., `integration_testing`, `documentation`) are excluded.

### Per-Domain Active Profiles

```json
{
  "skill_domains": {
    "documentation": {
      "active_profiles": ["documentation"],
      "bundle": "pm-documents"
    }
  }
}
```

Per-domain overrides take precedence over the global setting for that domain.

### CLI Management

```bash
# Show current config
manage-config skill-domains active-profiles

# Set global default
manage-config skill-domains active-profiles set --profiles implementation,module_testing,quality

# Set per-domain override
manage-config skill-domains active-profiles set --domain documentation --profiles documentation

# Remove per-domain override (falls back to global)
manage-config skill-domains active-profiles remove --domain documentation

# Remove global default (falls back to signal detection)
manage-config skill-domains active-profiles remove
```

## Validation Rules

1. **System domain required**: `skill_domains.system` must exist
2. **Workflow skills required**: `system.workflow_skills` must have all 6 phases
3. **Task executors required**: `system.task_executors` must exist with at least `implementation`
4. **Profile structure**: If domain has profiles, must have at least `core`
5. **Extension types**: Only `outline` and `triage` are valid extension types
6. **Skill format**: All skills must be `bundle:skill` format

## Reserved Keys

These keys are reserved in domain configuration and cannot be used as profile names:

- `workflow_skills` - System domain only
- `task_executors` - System domain only
- `workflow_skill_extensions` - Domain extensions
- `active_profiles` - Profile filtering (global or per-domain)
- `core` - Core skills for all profiles
- `defaults` - Top-level defaults (flat structure compatibility)
- `optionals` - Top-level optionals (flat structure compatibility)
