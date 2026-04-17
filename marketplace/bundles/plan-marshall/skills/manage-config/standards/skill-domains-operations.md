# Skill Domains Operations

Operational workflows for skill resolution, domain management, and usage patterns.

> **Core definitions**: For domain structure, profile model, field definitions, and validation rules, see [skill-domains.md](skill-domains.md).

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

### Execute-Task Skill Resolution

```bash
# Resolves profile to execute-task skill from system.execute_task_skills
manage-config resolve-execute-task-skill --profile implementation
# Returns: plan-marshall:execute-task

manage-config resolve-execute-task-skill --profile module_testing
# Returns: plan-marshall:execute-task
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
