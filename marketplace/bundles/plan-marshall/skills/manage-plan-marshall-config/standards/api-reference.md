# API Reference

Complete noun-verb API for plan-marshall-config.

## Execution Pattern

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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

**Profile-based update (6-phase model):**
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
  triage: pm-dev-java:ext-triage-java
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
- Always configures the `system` domain with task_executors
- Applies domain templates for each selected domain
- Collects verify steps from domain extensions via `provides_verify_steps()`

---

## Standalone Commands (Skill Resolution)

### resolve-workflow-skill-extension

Resolve domain-specific workflow skill extension. Returns null (not error) if extension doesn't exist.

**Extension Types:**
- `outline` - Additional context for solution-outline phase
- `triage` - Finding triage logic for execute (verification) and finalize phases

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

**Profiles:** implementation, module_testing, integration_testing, quality

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

### get-skills-by-profile

Get skills organized by profile for a domain. Loads profiles from extension.py via bundle reference.

```bash
plan-marshall-config get-skills-by-profile --domain java
```

**Output:**
```toon
status: success
domain: java
skills_by_profile:
  implementation: ["pm-dev-java:java-core", "pm-dev-java:java-null-safety", "pm-dev-java:java-cdi"]
  module_testing: ["pm-dev-java:java-core", "pm-dev-java:junit-core"]
  integration_testing: ["pm-dev-java:java-core", "pm-dev-java:junit-core", "pm-dev-java:junit-integration"]
  documentation: ["pm-dev-java:java-core", "pm-dev-java:javadoc"]
```

### configure-task-executors

Auto-discover profiles from configured domains and register task executors.
Convention: profile X maps to skill `pm-workflow:task-X`.

```bash
plan-marshall-config configure-task-executors
```

**Output:**
```toon
status: success
task_executors_configured: 3
executors:
  implementation: pm-workflow:task-implementation
  integration_testing: pm-workflow:task-integration_testing
  module_testing: pm-workflow:task-module_testing
```

### resolve-task-executor

Resolve task executor skill for a given profile.

```bash
plan-marshall-config resolve-task-executor --profile implementation
```

**Output:**
```toon
status: success
profile: implementation
task_executor: pm-workflow:task-implementation
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

Manage phase-specific plan configuration. Each phase has its own sub-noun.

### phase-1-init get

Get init phase configuration.

```bash
plan-marshall-config plan phase-1-init get
```

### phase-1-init set

Set init phase field.

```bash
plan-marshall-config plan phase-1-init set \
  --field branch_strategy --value feature
```

### phase-2-refine get

Get refine phase configuration.

```bash
plan-marshall-config plan phase-2-refine get
```

### phase-2-refine set

Set refine phase field.

```bash
plan-marshall-config plan phase-2-refine set \
  --field compatibility --value deprecation
```

### phase-5-execute get

Get execute phase configuration.

```bash
plan-marshall-config plan phase-5-execute get
```

### phase-5-execute set

Set execute phase field.

```bash
plan-marshall-config plan phase-5-execute set \
  --field commit_strategy --value per_plan
```

### phase-5-execute get (verification settings)

Get execute phase configuration including verification generic steps and domain steps.

```bash
plan-marshall-config plan phase-5-execute get
```

Optional `--field` to get a specific field:

```bash
plan-marshall-config plan phase-5-execute get --field verification_max_iterations
```

### phase-5-execute set-max-iterations

Set maximum verification iterations.

```bash
plan-marshall-config plan phase-5-execute set-max-iterations --value 10
```

### phase-5-execute set-step

Enable or disable a generic boolean verification step.

```bash
plan-marshall-config plan phase-5-execute set-step \
  --step verification_1_quality_check --enabled false
```

### phase-5-execute set-domain-step

Enable or disable a domain verification step.

```bash
plan-marshall-config plan phase-5-execute set-domain-step \
  --domain java --step 1_technical_impl --enabled false
```

### phase-5-execute set-domain-step-agent

Set a domain verification step's agent reference.

```bash
plan-marshall-config plan phase-5-execute set-domain-step-agent \
  --domain java --step 1_technical_impl --agent pm-dev-java:java-verify-agent
```

### phase-6-finalize get

Get finalize phase configuration.

```bash
plan-marshall-config plan phase-6-finalize get
```

### phase-6-finalize set-max-iterations

Set maximum finalize iterations.

```bash
plan-marshall-config plan phase-6-finalize set-max-iterations --value 5
```

### phase-6-finalize set-step

Enable or disable a finalize step.

```bash
plan-marshall-config plan phase-6-finalize set-step \
  --step 2_create_pr --enabled false
```

---

## Noun: ext-defaults

Manage extension defaults (generic key-value storage for extension-set configuration).

### get

Get extension default value by key.

```bash
plan-marshall-config ext-defaults get --key my_setting
```

**Output:**
```toon
status: success
key: my_setting
value: my_value
```

### set

Set extension default value (always overwrites).

```bash
plan-marshall-config ext-defaults set --key my_setting --value my_value
```

### set-default

Set value only if key does not exist (write-once).

```bash
plan-marshall-config ext-defaults set-default --key my_setting --value my_value
```

**Output (key exists):**
```toon
status: skipped
key: my_setting
reason: key_exists
existing_value: old_value
```

### list

List all extension defaults.

```bash
plan-marshall-config ext-defaults list
```

**Output:**
```toon
status: success
extension_defaults:
  key1: value1
  key2: value2
count: 2
```

### remove

Remove extension default by key.

```bash
plan-marshall-config ext-defaults remove --key my_setting
```

---

## Noun: ci (additional verbs)

### persist

Persist full CI config (provider, commands, tools) in a single operation.

```bash
plan-marshall-config ci persist \
  --provider github \
  --repo-url "https://github.com/org/repo" \
  --commands '{"issue-view": "gh issue view", "pr-create": "gh pr create"}' \
  --tools "gh" \
  --git-present true
```

**Output:**
```toon
status: success
provider: github
repo_url: https://github.com/org/repo
commands_count: 2
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
