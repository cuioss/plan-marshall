---
name: manage-config
description: Project-level infrastructure configuration for marshal.json
user-invocable: false
scope: hybrid
---

# Manage Config Skill

Manages project-level infrastructure configuration in `.plan/marshal.json`.

**Scope: hybrid** means this skill manages project-level settings (marshal.json persists across plans) while also providing plan-phase-specific configuration (branching, commit strategy, verification steps).

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify marshal.json directly; all mutations go through the script API
- Do not invent script arguments not listed in the API Reference
- Do not bypass initialization (marshal.json must exist before queries)

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config {command} {args}`
- Domain configuration follows the noun-verb pattern documented in the API Reference
- Phase configuration uses the `plan {phase} {verb}` pattern

## What This Skill Provides

- **Skill Domains**: Implementation skill defaults and optionals per domain
- **System Settings**: Retention and cleanup configuration
- **Plan Phase Configuration**: Phase-specific settings (branching, compatibility, commit strategy, pipelines)

## When to Activate This Skill

Activate this skill when:
- Initializing project configuration (`/marshall-steward` wizard)
- Querying implementation skills for a domain
- Managing retention settings
- Configuring plan phase settings

---

## Workflow: Initialize Configuration

**Pattern**: Script Automation

Initialize marshal.json with defaults.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config init
```

---

## Workflow: Query Skill Domains

**Pattern**: Read-Process-Write

Get implementation skills for a specific domain.

### Get Domain Defaults

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-defaults --domain java-core
```

**Output**:
```toon
status: success
domain: java-core
defaults[1]:
- pm-dev-java:java-core
```

### Get Domain Optionals

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-optionals --domain java-implementation
```

### Validate Skill in Domain

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains validate --domain java-core --skill pm-dev-java:java-lombok
```

---

## Workflow: System Settings

**Pattern**: Read-Process-Write

Manage system-level infrastructure settings.

### Get Retention Settings

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  system retention get
```

### Set Retention Field

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  system retention set --field logs_days --value 7
```

---

## Workflow: Plan Phase Configuration

**Pattern**: Read-Process-Write

Manage phase-specific plan configuration. Each phase has its own sub-noun.

### Get Phase Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get
```

### Get Specific Phase Field

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field compatibility
```

### Set Phase Field

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_strategy --value per_plan
```

---

## Workflow: CI Operations

CI operations use the provider-agnostic `ci` router. The router reads `ci.provider` from marshal.json and delegates to the correct provider script (github.py or gitlab.py).

**Note**: CI commands use a different notation — they route through `tools-integration-ci`, not `manage-config`. The config skill only stores the CI provider/tools settings; actual CI operations are in the `workflow-integration-ci` and `workflow-integration-git` skills.

### Example: View Issue

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view --issue 123
```

### Available CI Operations

- `pr create` / `pr view` / `pr list` / `pr merge` / `pr close` / `pr ready` / `pr edit`
- `pr reviews` / `pr comments` / `pr reply` / `pr resolve-thread` / `pr thread-reply`
- `pr auto-merge`
- `ci status` / `ci wait` / `ci rerun` / `ci logs`
- `issue create` / `issue view` / `issue close`

---

## API Reference

### Noun: skill-domains

| Verb | Parameters | Purpose |
|------|------------|---------|
| `list` | (none) | List all domains |
| `get` | `--domain` | Get full domain config (returns nested structure for technical domains) |
| `get-defaults` | `--domain` | Get default skills (returns `core.defaults` for nested domains) |
| `get-optionals` | `--domain` | Get optional skills (returns `core.optionals` for nested domains) |
| `set` | `--domain [--profile] [--defaults] [--optionals]` | Set domain config (profiles read from extension.py, system domain only) |
| `add` | `--domain --defaults [--optionals]` | Add new domain |
| `validate` | `--domain --skill` | Check if skill valid (searches all profiles for nested domains) |
| `detect` | (none) | Auto-detect domains from project files |
| `get-extensions` | `--domain` | Get workflow skill extensions for domain |
| `set-extensions` | `--domain --type --skill` | Set workflow skill extension (types: outline, triage) |
| `get-available` | (none) | Get available domains based on detected build systems |
| `configure` | `--domains` | Configure selected domains with templates |

### resolve-domain-skills

| Parameters | Purpose |
|------------|---------|
| `--domain --profile` | Resolve skills for domain and profile (aggregates `{domain}.core` + `{domain}.{profile}`) |

Standard profiles: `implementation`, `module_testing`, `integration_testing`, `quality`.

### resolve-workflow-skill

| Parameters | Purpose |
|------------|---------|
| `--phase` | Resolve system workflow skill for phase (init, refine, outline, plan, execute, verify, finalize) |

Always returns from the `system` domain's `workflow_skills`.

### resolve-workflow-skill-extension

| Parameters | Purpose |
|------------|---------|
| `--domain --type` | Resolve domain-specific workflow extension (types: outline, triage) |

Extension types:
- **outline**: Loaded during phase-3-outline to provide domain-specific component discovery and assessment logic
- **triage**: Loaded during phase-6-finalize to provide domain-specific finding triage (e.g., Java compilation vs JS lint errors)

Returns null (not error) if extension doesn't exist for the domain.

### get-workflow-skills

| Parameters | Purpose |
|------------|---------|
| (none) | Get all workflow skills from system domain (6-phase model) |

### get-skills-by-profile

| Parameters | Purpose |
|------------|---------|
| `--domain` | Get skills organized by profile for architecture enrichment |

### configure-task-executors

| Parameters | Purpose |
|------------|---------|
| (none) | Auto-discover profiles from all configured domains and register task executors. Convention: profile X maps to `plan-marshall:task-X` (e.g., `implementation` → `plan-marshall:task-implementation`). Scans extension.py for each domain's profile definitions. |

### resolve-task-executor

| Parameters | Purpose |
|------------|---------|
| `--profile` | Resolve task executor skill for a profile (e.g., implementation, module_testing) |

### Noun: ext-defaults

Extension defaults store key-value pairs used by domain extension bundles to persist user choices across plans (e.g., preferred build profiles, selected technologies). Extensions read these to avoid re-prompting.

| Verb | Parameters | Purpose |
|------|------------|---------|
| `get` | `--key` | Get extension default value |
| `set` | `--key --value` | Set extension default value (always overwrites) |
| `set-default` | `--key --value` | Set value only if key does not exist (write-once) |
| `list` | (none) | List all extension defaults |
| `remove` | `--key` | Remove extension default |

### Noun: system

| Verb | Parameters | Purpose |
|------|------------|---------|
| `retention get` | (none) | Get all retention settings |
| `retention set` | `--field --value` | Set retention field |

**Retention fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `logs_days` | int | 1 | Days to keep global log files |
| `archived_plans_days` | int | 5 | Days to keep archived plan directories |
| `memory_days` | int | 5 | Days to keep memory files |
| `temp_on_maintenance` | bool | true | Clean `.plan/temp/` during maintenance |

### Noun: plan

Phase-specific configuration using `plan {phase} {verb}` pattern.

**Phase field reference:**

| Phase | Field | Valid Values | Description |
|-------|-------|-------------|-------------|
| `phase-1-init` | `branch_strategy` | `feature`, `hotfix`, `release` | Branch naming prefix |
| `phase-2-refine` | `confidence_threshold` | 0-100 (int) | Confidence level required to exit refinement |
| `phase-2-refine` | `compatibility` | `breaking`, `deprecation`, `smart_and_ask` | How to handle API compatibility |
| `phase-5-execute` | `commit_strategy` | `per_deliverable`, `per_plan` | When to create git commits |
| `phase-5-execute` | `steps` | list (via set-steps) | Verification steps pipeline |
| `phase-5-execute` | `verification_max_iterations` | int | Max verify-fix iterations |
| `phase-6-finalize` | `steps` | list (via set-steps) | Finalization steps pipeline |
| `phase-6-finalize` | `max_iterations` | int | Max finalize iterations |
| `phase-6-finalize` | `review_bot_buffer_seconds` | int | Wait time for review bots |

| Verb | Parameters | Purpose |
|------|------------|---------|
| `phase-1-init get` | `[--field]` | Get init phase configuration |
| `phase-1-init set` | `--field --value` | Set init phase field (branch_strategy) |
| `phase-2-refine get` | `[--field]` | Get refine phase configuration |
| `phase-2-refine set` | `--field --value` | Set refine phase field (confidence_threshold, compatibility) |
| `phase-5-execute get` | `[--field]` | Get execute phase configuration (includes verification steps) |
| `phase-5-execute set` | `--field --value` | Set execute phase field (commit_strategy) |
| `phase-5-execute set-steps` | `--steps` | Replace entire verify steps list (comma-separated) |
| `phase-5-execute add-step` | `--step [--position]` | Add step to verify list |
| `phase-5-execute remove-step` | `--step` | Remove step from verify list |
| `phase-5-execute set-max-iterations` | `--value` | Set verification max iterations |
| `phase-6-finalize get` | (none) | Get finalize phase configuration |
| `phase-6-finalize set-steps` | `--steps` | Replace entire finalize steps list (comma-separated) |
| `phase-6-finalize add-step` | `--step [--position]` | Add step to finalize list |
| `phase-6-finalize remove-step` | `--step` | Remove step from finalize list |
| `phase-6-finalize set-max-iterations` | `--value` | Set finalize max iterations |

### Noun: ci

| Verb | Parameters | Purpose |
|------|------------|---------|
| `get` | (none) | Get full CI config |
| `get-provider` | (none) | Get CI provider and repo URL |
| `get-tools` | (none) | Get authenticated tools list |
| `get-command` | `--name` | Get single CI command by name (ready to execute) |
| `set-provider` | `--provider --repo-url` | Set CI provider |
| `set-tools` | `--tools` | Set authenticated tools (comma-separated) |
| `persist` | `--provider --repo-url [--commands] [--tools] [--git-present]` | Persist full CI config (provider, commands, tools) |

### init

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  init [--force]
```

---

## Data Model

### marshal.json Location

`.plan/marshal.json`

### Structure

The defaults template contains only `system` domain. Technical domains (java, javascript, etc.) are added during project initialization based on detection or manual configuration. Technical domains store only `bundle` reference and `workflow_skill_extensions` -- profiles are loaded at runtime from `extension.py`.

**Example** (Java project after init):

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:dev-general-practices"],
      "optionals": ["plan-marshall:dev-general-practices"],
      "task_executors": {
        "implementation": "plan-marshall:task-implementation",
        "module_testing": "plan-marshall:task-module-testing",
        "integration_testing": "plan-marshall:task-integration_testing"
      }
    },
    "java": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  },
  "system": {
    "retention": {
      "logs_days": 1,
      "archived_plans_days": 5,
      "memory_days": 5,
      "temp_on_maintenance": true
    }
  },
  "plan": {
    "phase-1-init": {
      "branch_strategy": "feature"
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking"
    },
    "phase-5-execute": {
      "commit_strategy": "per_deliverable",
      "verification_max_iterations": 5,
      "steps": ["quality_check", "build_verify"]
    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 300,
      "steps": [
        "commit_push", "create_pr", "automated_review",
        "sonar_roundtrip", "knowledge_capture", "lessons_capture",
        "branch_cleanup", "archive"
      ]
    }
  }
}
```

---

## Standard Domains

### System Domain

The `system` domain contains task executors and base skills applied to all tasks.

| Field | Purpose |
|-------|---------|
| `defaults` | Base skills loaded for all tasks (`plan-marshall:dev-general-practices`) |
| `optionals` | Optional base skills available for selection |
| `task_executors` | Maps profiles to task executor skills (convention: profile X -> `plan-marshall:task-X`) |

### Technical Domains (Profile Structure)

Technical domains store `bundle` reference and `workflow_skill_extensions` in marshal.json. Profiles are loaded at runtime from `extension.py`.

| Profile | Phase | Purpose |
|---------|-------|---------|
| `core` | all | Skills loaded for all profiles |
| `implementation` | execute | Production code tasks |
| `module_testing` | execute | Unit/module test tasks |
| `integration_testing` | execute | Integration test tasks |
| `quality` | verify | Documentation, verification |

**Available Domains**:

| Domain | Bundle | Extensions |
|--------|--------|------------|
| `java` | `pm-dev-java` | triage |
| `javascript` | `pm-dev-frontend` | triage |
| `plan-marshall-plugin-dev` | `pm-plugin-development` | outline, triage |
| `documentation` | `pm-documents` | outline, triage |

Use `resolve-domain-skills --domain {domain} --profile {profile}` to get aggregated skills.

---

## Scripts

| Script | Notation |
|--------|----------|
| manage-config | `plan-marshall:manage-config` |

Script characteristics:
- Uses Python stdlib only (json, argparse, pathlib, xml.etree)
- Outputs TOON to stdout
- Exit code 0 for success, 1 for errors
- Supports `--help` flag

---

## Integration Points

### With plan-marshall Skill
- Called during wizard initialization
- Called from configuration menus

### With Implementation Agents
- `skill-domains get-defaults` provides skills to load
- `skill-domains get-optionals` provides available optionals

### With Cleanup
- `system retention get` provides retention settings

---

## Error Responses

All operations validate prerequisites before proceeding. Standard error conditions:

| Error | Cause | Resolution |
|-------|-------|------------|
| `not_initialized` | marshal.json missing | Run `/marshall-steward` |
| `invalid_domain` | Domain not in skill_domains | Check domain name or run `/marshall-steward` |
| `skill_domains not configured` | No domains in marshal.json | Run `/marshall-steward` |
| `invalid_field` | Unknown field for phase/noun | Check field reference table above |
| `skill_not_found` | Skill not in domain defaults/optionals | Check with `validate --domain --skill` |

```toon
status: error
error: not_initialized
message: Project configuration not initialized. Run init first.
```

---

## Related Skills

- `manage-architecture` — Consumes configuration for project analysis
- `marshall-steward` — Interactive configuration wizard
- `extension-api` — Build system detection uses config
