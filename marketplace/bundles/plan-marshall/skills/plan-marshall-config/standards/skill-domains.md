# Skill Domains

Implementation skill management with profile-based structure and workflow skill extensions.

## Purpose

Skill domains configure which implementation skills are loaded when working on code in different domains. The structure supports:

- **System Domain**: Contains workflow skills for the 5-phase execution model
- **Technical Domains**: Language-specific with profiles and workflow skill extensions (java, javascript)

## 5-Phase Workflow Model

The system domain contains workflow skills for the 5 execution phases:

| Phase | Purpose | Workflow Skill |
|-------|---------|----------------|
| `init` | Initialize plan | `pm-workflow:plan-init` |
| `outline` | Create solution outline | `pm-workflow:phase-refine-outline` |
| `plan` | Decompose into tasks | `pm-workflow:task-plan` |
| `execute` | Run implementation | `pm-workflow:task-execute` |
| `finalize` | Commit, PR, quality | `pm-workflow:plan-finalize` |

## Structure

### System Domain Structure

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:general-development-rules"],
      "optionals": ["plan-marshall:diagnostic-patterns"],
      "workflow_skills": {
        "init": "pm-workflow:plan-init",
        "outline": "pm-workflow:phase-refine-outline",
        "plan": "pm-workflow:task-plan",
        "execute": "pm-workflow:task-execute",
        "finalize": "pm-workflow:plan-finalize"
      }
    }
  }
}
```

### Technical Domain Structure (Profile-Based)

```json
{
  "skill_domains": {
    "java": {
      "workflow_skill_extensions": {
        "outline": "pm-dev-java:java-outline-ext",
        "triage": "pm-dev-java:java-triage"
      },
      "core": {
        "defaults": ["pm-dev-java:java-core"],
        "optionals": ["pm-dev-java:java-null-safety", "pm-dev-java:java-lombok"]
      },
      "implementation": {
        "defaults": [],
        "optionals": ["pm-dev-java:java-cdi", "pm-dev-java:java-maintenance"]
      },
      "testing": {
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
| `triage` | finalize | Finding decision-making (fix/suppress/accept) |

### Profiles

| Profile | Phase Used | Purpose |
|---------|------------|---------|
| `implementation` | execute (impl tasks) | Production code patterns |
| `testing` | execute (test tasks) | Test code patterns |
| `quality` | finalize | Verification, documentation standards |

### core

Foundation skills always included when the domain is selected.

```json
"core": {
  "defaults": ["pm-dev-java:java-core"],
  "optionals": ["pm-dev-java:java-null-safety", "pm-dev-java:java-lombok"]
}
```

## System Domain

Applied to all agents and skills. Contains workflow skills for the 5-phase model.

| Field | Content |
|-------|---------|
| defaults | `plan-marshall:general-development-rules` |
| optionals | `plan-marshall:diagnostic-patterns` |
| workflow_skills | 5 phases: init, outline, plan, execute, finalize |

## Technical Domains

### java

Java development with CDI, JUnit, and standard patterns.

**workflow_skill_extensions**:
| Type | Skill |
|------|-------|
| outline | `pm-dev-java:java-outline-ext` |
| triage | `pm-dev-java:java-triage` |

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

**testing**:
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

JavaScript/Frontend development with Jest and Cypress testing.

**workflow_skill_extensions**:
| Type | Skill |
|------|-------|
| outline | `pm-dev-frontend:js-outline-ext` |
| triage | `pm-dev-frontend:javascript-triage` |

**core**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-frontend:cui-javascript` |
| optionals | `pm-dev-frontend:cui-jsdoc`, `pm-dev-frontend:cui-javascript-project` |

**implementation**:
| Field | Skills |
|-------|--------|
| defaults | (none) |
| optionals | `pm-dev-frontend:cui-javascript-linting`, `pm-dev-frontend:cui-javascript-maintenance` |

**testing**:
| Field | Skills |
|-------|--------|
| defaults | `pm-dev-frontend:cui-javascript-unit-testing` |
| optionals | `pm-dev-frontend:cui-cypress` |

## Skill Resolution

### resolve-workflow-skill Command

Resolves the system workflow skill for a phase. Always returns from the `system` domain.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --phase outline
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--phase` | string | Yes | Phase name (init, outline, plan, execute, finalize) |

**Output**:
```toon
status: success
phase: outline
workflow_skill: pm-workflow:phase-refine-outline
```

**Error Cases**:
- System domain missing → `error: System domain not configured. Run /marshall-steward to initialize.`
- Unknown phase → `error: Unknown phase: {phase}. Available: init, outline, plan, execute, finalize`

### resolve-workflow-skill-extension Command

Resolves domain-specific workflow skill extension. Returns null (not error) if extension doesn't exist.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
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
extension: pm-dev-java:java-triage
```

### resolve-domain-skills Command

Aggregates `{domain}.core` + `{domain}.{profile}` skills with descriptions.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-domain-skills --domain java --profile implementation
```

**Output**:
```toon
status: success
domain: java
profile: implementation

defaults:
  pm-dev-java:java-core: Java patterns, CUI conventions, CuiLogger, null-safety

optionals:
  pm-dev-java:java-null-safety: JSpecify annotations (@NullMarked, @Nullable)
  pm-dev-java:java-lombok: Lombok annotations (@Builder, @Value, @Delegate)
  pm-dev-java:java-cdi: CDI patterns (@ApplicationScoped, @Inject)
  pm-dev-java:java-maintenance: Code maintenance and refactoring patterns
```

### get-workflow-skills Command

Returns all workflow skills from the system domain (5-phase model).

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  get-workflow-skills
```

**Output**:
```toon
status: success
init: pm-workflow:plan-init
outline: pm-workflow:phase-refine-outline
plan: pm-workflow:task-plan
execute: pm-workflow:task-execute
finalize: pm-workflow:plan-finalize
```

### Aggregation Logic

| Profile | Defaults | Optionals |
|---------|----------|-----------|
| `architecture` | `{domain}.core.defaults` + `{domain}.architecture.defaults` | `{domain}.core.optionals` + `{domain}.architecture.optionals` |
| `planning` | `{domain}.core.defaults` + `{domain}.planning.defaults` | `{domain}.core.optionals` + `{domain}.planning.optionals` |
| `implementation` | `{domain}.core.defaults` + `{domain}.implementation.defaults` | `{domain}.core.optionals` + `{domain}.implementation.optionals` |
| `testing` | `{domain}.core.defaults` + `{domain}.testing.defaults` | `{domain}.core.optionals` + `{domain}.testing.optionals` |
| `quality` | `{domain}.core.defaults` + `{domain}.quality.defaults` | `{domain}.core.optionals` + `{domain}.quality.optionals` |

## Usage Patterns

### Get Domain Configuration

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains get --domain java
```

Returns full nested structure including workflow_skill_extensions, core, and all profiles.

### Get Domain Extensions

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains get-extensions --domain java
```

Returns only the workflow_skill_extensions for the domain.

### Validate Skill in Domain

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
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
  "testing": {
    "defaults": ["pm-dev-python:pytest-core"],
    "optionals": []
  },
  "quality": {
    "defaults": [],
    "optionals": []
  }
}
```

No agent changes needed - agents work with any domain.

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
- Use `testing` for test code tasks
- Use `quality` for verification and documentation
- Core skills apply to all profiles
