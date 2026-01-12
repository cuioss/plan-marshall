# API Reference

Complete noun-verb API for plan-marshall-config.

## Execution Pattern

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  {noun} {verb} [--param value]
```

## Noun: skill-domains

Manage implementation skill defaults and optionals per domain.

### list

List all configured domains.

```bash
plan-marshall-config skill-domains list
```

**Output:**
```toon
status: success
domains[8]:
- system
- plugin-development
- java-core
- java-implementation
- java-testing
- javascript-core
- javascript-implementation
- javascript-testing
count: 8
```

### get

Get full domain configuration.

```bash
plan-marshall-config skill-domains get --domain java-core
```

**Output:**
```toon
status: success
domain: java-core
defaults[1]:
- pm-dev-java:java-core
optionals[3]:
- pm-dev-java:java-null-safety
- pm-dev-java:java-lombok
- pm-dev-java:javadoc
```

### get-defaults

Get default skills for a domain.

```bash
plan-marshall-config skill-domains get-defaults --domain java-core
```

### get-optionals

Get optional skills for a domain.

```bash
plan-marshall-config skill-domains get-optionals --domain java-implementation
```

### set

Update domain configuration. Supports both flat structure (backward compatible) and profile-based updates.

**Flat structure (backward compatible):**
```bash
plan-marshall-config skill-domains set \
  --domain java-core \
  --defaults "pm-dev-java:java-core,pm-dev-java:java-null-safety" \
  --optionals "pm-dev-java:java-lombok,pm-dev-java:javadoc"
```

**Profile-based update (5-phase model):**
```bash
plan-marshall-config skill-domains set \
  --domain java \
  --profile implementation \
  --defaults "pm-dev-java:java-core" \
  --optionals "pm-dev-java:java-cdi,pm-dev-java:java-maintenance"
```

**Output:**
```toon
status: success
domain: java
profile: implementation
updated:
  defaults: ["pm-dev-java:java-core"]
  optionals: ["pm-dev-java:java-cdi", "pm-dev-java:java-maintenance"]
```

### add

Add a new domain.

```bash
plan-marshall-config skill-domains add \
  --domain python \
  --defaults "pm-dev-python:cui-python-core"
```

### validate

Check if a skill is valid for a domain. For nested domains, validates across all profiles.

```bash
plan-marshall-config skill-domains validate \
  --domain java \
  --skill pm-dev-java:java-lombok
```

**Output:**
```toon
status: success
domain: java
skill: pm-dev-java:java-lombok
valid: true
in_defaults: false
in_optionals: true
```

### detect

Auto-detect domains from project files and add to configuration.

```bash
plan-marshall-config skill-domains detect
```

**Output:**
```toon
status: success
detected: ["java", "javascript"]
count: 2
message: Detected domains: java, javascript
```

### get-extensions

Get workflow skill extensions for a domain.

```bash
plan-marshall-config skill-domains get-extensions --domain java
```

**Output:**
```toon
status: success
domain: java
extensions:
  outline: pm-dev-java:java-outline-ext
  triage: pm-dev-java:java-triage
```

### set-extensions

Set a workflow skill extension for a domain.

**Extension Types:**
- `outline` - Domain-specific patterns for solution-outline phase
- `triage` - Domain-specific finding decision logic for plan-finalize phase

```bash
plan-marshall-config skill-domains set-extensions \
  --domain java \
  --type outline \
  --skill pm-dev-java:java-outline-ext
```

**Output:**
```toon
status: success
domain: java
type: outline
skill: pm-dev-java:java-outline-ext
```

### get-available

Get available domains based on detected build systems. Used by wizard integration.

```bash
plan-marshall-config skill-domains get-available
```

**Output:**
```toon
status: success
detected_domains[1]:
- key: java
  name: Java Development
  build_system: maven
optional_domains[2]:
- key: requirements
  name: Requirements Engineering
- key: documentation
  name: Documentation
```

### configure

Configure selected domains with templates. Always adds the system domain.

```bash
plan-marshall-config skill-domains configure --domains "java,javascript"
```

**Output:**
```toon
status: success
system_domain: configured
domains_configured: 2
domains: java,javascript
```

**Note:** This command:
- Always configures the `system` domain with workflow_skills
- Applies DOMAIN_TEMPLATES for each selected domain
- Creates full profile structure for each domain

---

## Standalone Commands (Skill Resolution)

### resolve-workflow-skill

Resolve system workflow skill for a phase. Always returns from the `system` domain.

**Phases:** init, outline, plan, execute, finalize

```bash
plan-marshall-config resolve-workflow-skill --phase outline
```

**Output:**
```toon
status: success
phase: outline
workflow_skill: pm-workflow:phase-refine-outline
```

### resolve-workflow-skill-extension

Resolve domain-specific workflow skill extension. Returns null (not error) if extension doesn't exist.

**Extension Types:**
- `outline` - Additional context for solution-outline phase
- `triage` - Finding triage logic for plan-finalize phase

```bash
plan-marshall-config resolve-workflow-skill-extension \
  --domain java --type outline
```

**Output (extension exists):**
```toon
status: success
domain: java
type: outline
extension: pm-dev-java:java-outline-ext
```

**Output (no extension):**
```toon
status: success
domain: javascript
type: triage
extension: null
```

### resolve-domain-skills

Resolve all skills for a domain and profile. Returns core + profile skills.

**Profiles:** implementation, testing, quality

```bash
plan-marshall-config resolve-domain-skills \
  --domain java --profile implementation
```

**Output:**
```toon
status: success
domain: java
profile: implementation
defaults[1]:
  - pm-dev-java:java-core
    description: Core Java development patterns
optionals[2]:
  - pm-dev-java:java-cdi
    description: CDI/Quarkus patterns
  - pm-dev-java:java-maintenance
    description: Code maintenance standards
```

### get-workflow-skills

Get all workflow skills from the system domain (5-phase model).

```bash
plan-marshall-config get-workflow-skills
```

**Output:**
```toon
status: success
init: pm-workflow:phase-init
outline: pm-workflow:phase-refine-outline
plan: pm-workflow:phase-refine-plan
execute: pm-workflow:phase-execute
finalize: pm-workflow:phase-finalize
```

---

## Noun: system

Manage system-level settings.

### retention get

Get all retention settings.

```bash
plan-marshall-config system retention get
```

**Output:**
```toon
status: success
retention:
  logs_days: 1
  archived_plans_days: 5
  memory_days: 5
  temp_on_maintenance: true
```

### retention set

Set a retention field.

```bash
plan-marshall-config system retention set \
  --field logs_days \
  --value 7
```

---

## Noun: plan

Manage plan-related configuration.

### defaults list

List all plan defaults.

```bash
plan-marshall-config plan defaults list
```

**Output:**
```toon
status: success
defaults:
  compatibility: deprecations
  commit_strategy: phase-specific
  create_pr: false
  verification_required: true
  branch_strategy: direct
```

### defaults get

Get a specific default value.

```bash
plan-marshall-config plan defaults get --field commit_strategy
```

### defaults set

Set a default value.

```bash
plan-marshall-config plan defaults set \
  --field create_pr \
  --value true
```

---

## init

Initialize marshal.json.

```bash
plan-marshall-config init [--force]
```

**Output:**
```toon
status: success
created: .plan/marshal.json
build_systems_detected: 2
```

## Error Responses

All errors follow this pattern:

```toon
status: error
error: {message}
```

Common errors:
- `marshal.json not found. Run command /marshall-steward first`
- `skill_domains not configured. Run command /marshall-steward first`
- `Unknown domain: {name}`
