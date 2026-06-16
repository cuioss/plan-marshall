# Skill Domains Operations

Operational workflows for skill resolution, domain management, and usage patterns.

> **Core definitions**: For domain structure, profile model, field definitions, and validation rules, see [skill-domains.md](skill-domains.md).

## Skill Resolution

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
package_source: packages

defaults:
  pm-dev-java:java-core: Java patterns, conventions, null-safety

optionals:
  pm-dev-java:java-null-safety: JSpecify annotations (@NullMarked, @Nullable)
  pm-dev-java:java-lombok: Lombok annotations (@Builder, @Value, @Delegate)
  pm-dev-java:java-cdi: CDI patterns (@ApplicationScoped, @Inject)
  pm-dev-java:java-maintenance: Code maintenance and refactoring patterns
```

`package_source` is present only when the resolved profile declares it in its `extension.py` profile dict. Profiles that do not declare `package_source` (e.g., `core`, `quality`) omit the key from output.

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
