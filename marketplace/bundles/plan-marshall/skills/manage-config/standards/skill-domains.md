# Skill Domains

Implementation skill management with profile-based structure and workflow skill extensions.

## Purpose

Skill domains configure which implementation skills are loaded when working on code in different domains. The structure supports:

- **System Domain**: Contains workflow skills for the 6-phase execution model
- **Technical Domains**: Language-specific with profiles and workflow skill extensions (java, javascript)

## Schema Structure

See `data-model.md` for the complete `skill_domains` JSON schema. The key hierarchy is:

- `skill_domains.active_profiles[]` — globally active profiles
- `skill_domains.system` — workflow skills, task executors, system-level defaults/optionals
- `skill_domains.{domain}` — per-domain skills organized by profile with extensions

## 6-Phase Workflow Model

The system domain contains workflow skills for the 6 execution phases:

| Phase | Purpose | Workflow Skill |
|-------|---------|----------------|
| `1-init` | Initialize plan, detect artifacts | `plan-marshall:phase-1-init` |
| `2-refine` | Clarify request until confidence threshold | `plan-marshall:phase-2-refine` |
| `3-outline` | Create solution outline with deliverables | `plan-marshall:phase-3-outline` |
| `4-plan` | Transform deliverables into executable tasks | `plan-marshall:phase-4-plan` |
| `5-execute` | Execute individual tasks + verification | `plan-marshall:phase-5-execute` |
| `6-finalize` | Commit, push, PR creation | `plan-marshall:phase-6-finalize` |

## Structure

### System Domain Structure

The `system` domain is required and contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `defaults` | array | No | Base skills loaded for all tasks |
| `optionals` | array | No | Optional base skills available for selection |
| `workflow_skills` | object | Yes | Maps 6 phases to workflow skill references |
| `task_executors` | object | Yes | Maps profiles to task executor skills |

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:dev-general-practices"],
      "optionals": ["plan-marshall:dev-general-practices"],
      "workflow_skills": {
        "1-init": "plan-marshall:phase-1-init",
        "2-refine": "plan-marshall:phase-2-refine",
        "3-outline": "plan-marshall:phase-3-outline",
        "4-plan": "plan-marshall:phase-4-plan",
        "5-execute": "plan-marshall:phase-5-execute",
        "6-finalize": "plan-marshall:phase-6-finalize"
      }
    }
  }
}
```

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

### Technical Domain Structure (Profile-Based)

Technical domains (java, javascript, etc.) use profile-based organization:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow_skill_extensions` | object | No | Domain-specific extensions for phases |
| `core` | object | Yes | Core skills loaded for all profiles |
| `implementation` | object | No | Skills for execute phase (production code) |
| `module_testing` | object | No | Skills for execute phase (unit/module tests) |
| `integration_testing` | object | No | Skills for execute phase (integration tests) |
| `quality` | object | No | Skills for verify phase |

```json
{
  "skill_domains": {
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
}
```

## Domain Structure Components

### workflow_skill_extensions

Domain-specific extensions that augment workflow skills. Only in technical domains (not system).

| Type | Phase | Purpose |
|------|-------|---------|
| `outline` | outline | Domain detection, deliverable patterns |
| `triage` | execute (verification), finalize | Finding decision-making (fix/suppress/accept) |

### Profiles

| Profile | Phase Used | Purpose |
|---------|------------|---------|
| `implementation` | execute (impl tasks) | Production code patterns |
| `module_testing` | execute (unit/module test tasks) | Unit and module test patterns |
| `integration_testing` | execute (integration test tasks) | Integration test patterns |
| `quality` | verify | Documentation and quality standards |

> **Note**: `quality` is a config profile for skill resolution. `manage-tasks` has additional task-only profiles (`verification`, `standalone`) not mapped to config skill domains — see `ref-manage-contract` for the full profile model.

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

### core

Foundation skills always included when the domain is selected.

```json
"core": {
  "defaults": ["pm-dev-java:java-core"],
  "optionals": ["pm-dev-java:java-null-safety", "pm-dev-java:java-lombok"]
}
```

## Profile-to-Phase Mapping

| Profile | Phase | Use Case |
|---------|-------|----------|
| `implementation` | execute | Production code development tasks |
| `module_testing` | execute | Unit/module test development tasks |
| `integration_testing` | execute | Integration test development tasks |
| `quality` | verify | Documentation, verification, compliance |

## System Domain

Applied to all agents and skills. Contains workflow skills for the 6-phase model.

| Field | Content |
|-------|---------|
| defaults | `plan-marshall:dev-general-practices` |
| optionals | `plan-marshall:dev-general-practices` |
| workflow_skills | 6 phases: init, refine, outline, plan, execute, finalize |

## Technical Domains

### java

Java development with CDI, JUnit, and standard patterns.

**workflow_skill_extensions**:
| Type | Skill |
|------|-------|
| outline | `pm-dev-java:java-outline-ext` |
| triage | `pm-dev-java:ext-triage-java` |

**core**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-java:java-core` |
| optionals | `pm-dev-java:java-null-safety`, `pm-dev-java:java-lombok` |

**architecture**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-java:java-packages` |
| optionals | (none) |

**implementation**:
| Field | Skills |
|-------|--------|
| defaults | (none) |
| optionals | `pm-dev-java:java-cdi`, `pm-dev-java:java-maintenance` |

**module_testing**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-java:junit-core` |
| optionals | (none) |

**integration_testing**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-java:junit-core` |
| optionals | `pm-dev-java:junit-integration` |

**quality**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-java:javadoc` |
| optionals | (none) |

### javascript

JavaScript/Frontend development with Jest testing.

**workflow_skill_extensions**:
| Type | Skill |
|------|-------|
| outline | `pm-dev-frontend:js-outline-ext` |
| triage | `pm-dev-frontend:ext-triage-js` |

**core**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-frontend:javascript` |
| optionals | (none) |

**implementation**:
| Field | Skills |
|-------|--------|
| defaults | (none) |
| optionals | `pm-dev-frontend:lint-config` |

**module_testing**:
| Field | Skills |
|-------|--------|
| defaults | (none) |
| optionals | (none) |

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

## Skill Resolution

### resolve-workflow-skill Command

Resolves the system workflow skill for a phase. Always returns from the `system` domain.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill --phase 3-outline
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--phase` | string | Yes | Phase name (1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize) |

**Output**:
```toon
status: success
phase: 3-outline
workflow_skill: plan-marshall:phase-3-outline
```

**Error Cases**:
- System domain missing → `error: System domain not configured. Run /marshall-steward to initialize.`
- Unknown phase → `error: Unknown phase: {phase}. Available: 1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize`

### resolve-workflow-skill-extension Command

Resolves domain-specific workflow skill extension. Returns null (not error) if extension doesn't exist.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain java --type triage
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain` | string | Yes | Domain name (java, javascript, etc.) |
| `--type` | string | Yes | Extension type (outline, triage) |

**Output**:
```toon
status: success
domain: java
type: triage
extension: pm-dev-java:ext-triage-java
```

### resolve-domain-skills Command

Aggregates `{domain}.core` + `{domain}.{profile}` skills with descriptions.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain java --profile implementation
```

**Output**:
```toon
status: success
domain: java
profile: implementation

defaults:
  pm-dev-java:java-core: Java patterns, conventions, null-safety

optionals:
  pm-dev-java:java-null-safety: JSpecify annotations (@NullMarked, @Nullable)
  pm-dev-java:java-lombok: Lombok annotations (@Builder, @Value, @Delegate)
  pm-dev-java:java-cdi: CDI patterns (@ApplicationScoped, @Inject)
  pm-dev-java:java-maintenance: Code maintenance and refactoring patterns
```

### get-workflow-skills Command

Returns all workflow skills from the system domain (6-phase model).

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  get-workflow-skills
```

**Output**:
```toon
status: success
1-init: plan-marshall:phase-1-init
2-refine: plan-marshall:phase-2-refine
3-outline: plan-marshall:phase-3-outline
4-plan: plan-marshall:phase-4-plan
5-execute: plan-marshall:phase-5-execute
6-finalize: plan-marshall:phase-6-finalize
```

### Aggregation Logic

| Profile | Defaults | Optionals |
|---------|----------|-----------|
| `architecture` | `{domain}.core.defaults` + `{domain}.architecture.defaults` | `{domain}.core.optionals` + `{domain}.architecture.optionals` |
| `planning` | `{domain}.core.defaults` + `{domain}.planning.defaults` | `{domain}.core.optionals` + `{domain}.planning.optionals` |
| `implementation` | `{domain}.core.defaults` + `{domain}.implementation.defaults` | `{domain}.core.optionals` + `{domain}.implementation.optionals` |
| `module_testing` | `{domain}.core.defaults` + `{domain}.module_testing.defaults` | `{domain}.core.optionals` + `{domain}.module_testing.optionals` |
| `integration_testing` | `{domain}.core.defaults` + `{domain}.integration_testing.defaults` | `{domain}.core.optionals` + `{domain}.integration_testing.optionals` |
| `quality` | `{domain}.core.defaults` + `{domain}.quality.defaults` | `{domain}.core.optionals` + `{domain}.quality.optionals` |

### Task Executor Resolution

```bash
# Resolves profile to task executor skill from system.task_executors
manage-config resolve-task-executor --profile implementation
# Returns: plan-marshall:task-implementation

manage-config resolve-task-executor --profile module_testing
# Returns: plan-marshall:task-module-testing
```

### Domain Skills Resolution

```bash
# Returns core + profile skills
manage-config resolve-domain-skills --domain java --profile implementation
# Returns: java-core (from core.defaults) + java-cdi, java-maintenance (from implementation)
```

## Usage Patterns

### Get Domain Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get --domain java
```

Returns full nested structure including workflow_skill_extensions, core, and all profiles.

### Get Domain Extensions

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-extensions --domain java
```

Returns only the workflow_skill_extensions for the domain.

### Validate Skill in Domain

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains validate --domain java --skill pm-dev-java:junit-core
```

Searches all profiles (core, implementation, testing, quality) for nested domains.

## Adding New Domains

### Adding a Technical Domain

```json
"python": {
  "workflow_skill_extensions": {
    "outline": "pm-dev-python:python-outline-ext",
    "triage": "pm-dev-python:python-triage"
  },
  "core": {
    "defaults": ["pm-dev-python:python-core"],
    "optionals": ["pm-dev-python:python-typing"]
  },
  "implementation": {
    "defaults": [],
    "optionals": []
  },
  "module_testing": {
    "defaults": ["pm-dev-python:pytest-core"],
    "optionals": []
  },
  "integration_testing": {
    "defaults": [],
    "optionals": []
  },
  "quality": {
    "defaults": [],
    "optionals": []
  }
}
```

No agent changes needed - agents work with any domain.

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

## Best Practices

### Defaults

- Include skills **always needed** for the profile
- Keep defaults minimal to reduce context load
- Core coding standards belong in `core.defaults`

### Optionals

- Include specialized skills (CDI, specific frameworks)
- Include maintenance/refactoring skills
- Task planning agents select based on task requirements

### Profiles

- Use `architecture` for high-level design in outline phase
- Use `planning` for task decomposition patterns
- Use `implementation` for production code tasks
- Use `module_testing` for unit and module test tasks
- Use `integration_testing` for integration test tasks
- Use `quality` for verification and documentation
- Core skills apply to all profiles
