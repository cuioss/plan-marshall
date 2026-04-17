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

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not bypass initialization (marshal.json must exist before queries)
- Domain configuration follows the noun-verb pattern documented in the API Reference
- Phase configuration uses the `plan {phase} {verb}` pattern

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

### Manage Verification Steps

```bash
# Add a step to the verification pipeline
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute add-step --step sonar_check --position 2

# Replace all verification steps
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps "quality_check,build_verify,sonar_check"

# Remove a step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute remove-step --step sonar_check
```

### Resolve Skills for a Domain and Profile

```bash
# Get aggregated skills for java implementation profile
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain java --profile implementation

# Resolve execute-task skill for a profile
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-execute-task-skill --profile module_testing
```

### Extension Defaults

```bash
# Set a write-once default (only if key doesn't exist)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  ext-defaults set-default --key preferred_build_profile --value fast

# Get an extension default
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  ext-defaults get --key preferred_build_profile
```

---

## Workflow: CI Operations

CI operations use the provider-agnostic `ci` router. The router resolves the active provider by scanning `providers[]` in marshal.json for the entry with `category == "ci"` and deriving the key from its `skill_name` (e.g., `plan-marshall:workflow-integration-github` -> `github`), then delegates to the matching provider script.

**Note**: CI commands use a different notation — they route through `tools-integration-ci`, not `manage-config`. `providers[]` is the single source of truth for CI provider identity; `manage-config` does not store a separate CI provider block. Actual CI operations live in the `workflow-integration-github` (or `workflow-integration-gitlab`) and `workflow-integration-git` skills.

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

> Full API specification: See [standards/api-reference.md](standards/api-reference.md).

| Noun | Key Verbs |
|------|-----------|
| `skill-domains` | list, get, get-defaults, get-optionals, set, add, validate, detect, configure, get-extensions, set-extensions, get-available |
| `resolve-domain-skills` | `--domain --profile` (aggregates core + profile skills) |
| `resolve-workflow-skill` | `--phase` (resolve system workflow skill) |
| `resolve-workflow-skill-extension` | `--domain --type` (outline, triage) |
| `get-workflow-skills` | Get all workflow skills from system domain |
| `get-skills-by-profile` | `--domain` (skills organized by profile) |
| `configure-execute-task-skills` | Auto-discover profiles and register execute-task skills |
| `resolve-execute-task-skill` | `--profile` (resolve execute-task skill for profile) |
| `ext-defaults` | get, set, set-default, list, remove |
| `system` | retention get, retention set |
| `plan` | `{phase} get/set`, set-steps, add-step, remove-step, set-max-iterations |
| `ci` | get, get-provider, get-tools, get-command, set-provider, set-tools, persist |
| `init` | Initialize marshal.json (with optional `--force`) |

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
      "execute_task_skills": {
        "implementation": "plan-marshall:execute-task",
        "module_testing": "plan-marshall:execute-task",
        "integration_testing": "plan-marshall:execute-task"
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
      "review_bot_buffer_seconds": 180,
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

> **Detailed reference**: See [standards/skill-domains.md](standards/skill-domains.md) for domain structure, profiles, and validation rules. See [standards/skill-domains-operations.md](standards/skill-domains-operations.md) for resolution commands and usage patterns.

### System Domain

The `system` domain contains execute-task skills and base skills applied to all tasks.

| Field | Purpose |
|-------|---------|
| `defaults` | Base skills loaded for all tasks (`plan-marshall:dev-general-practices`) |
| `optionals` | Optional base skills available for selection |
| `execute_task_skills` | Maps profiles to execute-task skills (convention: profile X -> `plan-marshall:execute-task-X`) |

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

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `marshall-steward` | init, skill-domains configure | Initialize and configure domains |
| `manage-architecture` | skill-domains set, ext-defaults | Set domain skills from enrichment |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | plan get, resolve-domain-skills | Read plan config, resolve skills |
| `phase-4-plan` | resolve-execute-task-skill | Resolve execute-task skill for task profile |
| `phase-5-execute` | resolve-domain-skills | Load skills for task execution |
| `manage-run-config` | system retention get | Read retention settings for cleanup |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error | Cause | Resolution |
|-------|-------|------------|
| `not_initialized` | marshal.json missing | Run `/marshall-steward` |
| `invalid_domain` | Domain not in skill_domains | Check domain name or run `/marshall-steward` |
| `skill_domains not configured` | No domains in marshal.json | Run `/marshall-steward` |
| `invalid_field` | Unknown field for phase/noun | Check field reference table above |
| `skill_not_found` | Skill not in domain defaults/optionals | Check with `validate --domain --skill` |

---

## Related

- `manage-architecture` — Consumes configuration for project analysis
- `marshall-steward` — Interactive configuration wizard
- `extension-api` — Build system detection uses config
