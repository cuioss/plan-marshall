# API Reference

Complete noun-verb API for manage-config.

## Execution Pattern

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  {noun} {verb} [--param value]
```

## Noun: skill-domains

Manage implementation skill defaults and optionals per domain.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `list` | -- | List all configured domains |
| `get` | `--domain` | Get full domain configuration (defaults + optionals) |
| `get-defaults` | `--domain` | Get default skills for a domain |
| `get-optionals` | `--domain` | Get optional skills for a domain |
| `set` | `--domain`, `--defaults`, `--optionals`, optional `--profile` | Update domain configuration |
| `add` | `--domain`, `--defaults` | Add a new domain |
| `validate` | `--domain`, `--skill` | Check if a skill is valid for a domain |
| `detect` | -- | Auto-detect domains from project files |
| `get-extensions` | `--domain` | Get workflow skill extensions for a domain |
| `set-extensions` | `--domain`, `--type`, `--skill` | Set a workflow skill extension |
| `get-available` | -- | Get available domains based on detected build systems |
| `configure` | `--domains` | Configure selected domains with templates |

### Example: set (profile-based)

```bash
manage-config skill-domains set \
  --domain java \
  --profile implementation \
  --defaults "pm-dev-java:java-core" \
  --optionals "pm-dev-java:java-cdi,pm-dev-java:java-maintenance"
```

### Example: validate

```bash
manage-config skill-domains validate \
  --domain java \
  --skill pm-dev-java:java-lombok
```

Output includes `valid`, `in_defaults`, and `in_optionals` booleans.

### Extension Types

Used by `get-extensions` and `set-extensions`:

- `outline` - Domain-specific patterns for solution-outline phase
- `triage` - Domain-specific finding decision logic for plan-finalize phase

### configure Notes

- Always configures the `system` domain with task_executors
- Applies domain templates for each selected domain
- Collects verify steps from domain extensions via `provides_verify_steps()`

---

## Standalone Commands (Skill Resolution)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `resolve-workflow-skill-extension` | `--domain`, `--type` | Resolve domain-specific workflow skill extension (returns `null` if not found) |
| `resolve-domain-skills` | `--domain`, `--profile` | Resolve all skills for domain + profile (core + profile skills) |
| `get-skills-by-profile` | `--domain` | Get skills organized by profile for a domain |
| `configure-task-executors` | -- | Auto-discover profiles and register task executors |
| `resolve-task-executor` | `--profile` | Resolve task executor skill for a profile |

### Profiles

Used by `resolve-domain-skills` and `resolve-task-executor`: `implementation`, `module_testing`, `integration_testing`, `quality`

### Example: resolve-domain-skills

```bash
manage-config resolve-domain-skills \
  --domain java --profile implementation
```

Returns `defaults` and `optionals` arrays with skill references and descriptions.

### Example: configure-task-executors

```bash
manage-config configure-task-executors
```

Convention: profile X maps to skill `plan-marshall:task-X`.

### resolve-workflow-skill-extension Notes

Returns `extension: null` (not error) when no extension exists for the domain/type combination.

---

## Noun: system

Manage system-level settings.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `retention get` | -- | Get all retention settings |
| `retention set` | `--field`, `--value` | Set a retention field |

### Example: retention set

```bash
manage-config system retention set \
  --field logs_days \
  --value 7
```

Retention fields: `logs_days`, `archived_plans_days`, `memory_days`, `temp_on_maintenance`.

---

## Noun: plan

Manage phase-specific plan configuration. Each phase has its own sub-noun.

### Phase sub-nouns

| Sub-noun | Verbs | Description |
|----------|-------|-------------|
| `phase-1-init` | `get`, `set` | Init phase (e.g., `branch_strategy`) |
| `phase-2-refine` | `get`, `set` | Refine phase (e.g., `compatibility`) |
| `phase-5-execute` | `get`, `set`, `set-max-iterations`, `set-step`, `set-domain-step`, `set-domain-step-agent` | Execute phase |
| `phase-6-finalize` | `get`, `set-max-iterations`, `set-step` | Finalize phase |

### Basic get/set pattern

```bash
manage-config plan phase-1-init set \
  --field branch_strategy --value feature
```

### phase-5-execute additional verbs

```bash
# Set maximum verification iterations
manage-config plan phase-5-execute set-max-iterations --value 10

# Enable/disable a generic boolean verification step
manage-config plan phase-5-execute set-step \
  --step verification_1_quality_check --enabled false

# Enable/disable a domain verification step
manage-config plan phase-5-execute set-domain-step \
  --domain java --step 1_technical_impl --enabled false

# Set a domain verification step's agent reference
manage-config plan phase-5-execute set-domain-step-agent \
  --domain java --step 1_lint --agent my-bundle:my-verify-step
```

### phase-6-finalize additional verbs

```bash
# Set maximum finalize iterations
manage-config plan phase-6-finalize set-max-iterations --value 5

# Enable/disable a finalize step
manage-config plan phase-6-finalize set-step \
  --step 2_create_pr --enabled false
```

Optional `--field` parameter on `get` to retrieve a specific field:

```bash
manage-config plan phase-5-execute get --field verification_max_iterations
```

---

## Noun: ext-defaults

Manage extension defaults (generic key-value storage for extension-set configuration).

| Verb | Parameters | Description |
|------|-----------|-------------|
| `get` | `--key` | Get extension default value by key |
| `set` | `--key`, `--value` | Set value (always overwrites) |
| `set-default` | `--key`, `--value` | Set value only if key does not exist (write-once) |
| `list` | -- | List all extension defaults |
| `remove` | `--key` | Remove extension default by key |

### set-default behavior

When key already exists, returns `status: skipped` with `reason: key_exists` and `existing_value`.

### Example

```bash
manage-config ext-defaults set --key my_setting --value my_value
manage-config ext-defaults set-default --key my_setting --value fallback
```

---

## Noun: ci

### persist

Persist full CI config (provider, commands, tools) in a single operation.

```bash
manage-config ci persist \
  --provider github \
  --repo-url "https://github.com/org/repo" \
  --commands '{"issue-view": "gh issue view", "pr-create": "gh pr create"}' \
  --tools "gh" \
  --git-present true
```

---

## init

Initialize marshal.json.

```bash
manage-config init [--force]
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
