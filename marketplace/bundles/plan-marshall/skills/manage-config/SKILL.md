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

## Workflow: Sync Defaults

**Pattern**: Script Automation

Non-destructively merge any keys present in `get_default_config()` but missing
from the live `.plan/marshal.json` into the file, without overwriting existing
user values. This is the canonical migration path after a default-shape change
(new schema rows added to a `DEFAULT_*` block): existing projects never re-run
`init`, so `sync-defaults` is how a live `marshal.json` picks up new defaults
while preserving every operator override.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config sync-defaults
```

**Contract** (non-destructive deep merge):

- A key already present in the live config is preserved unchanged. "Present"
  means "key exists" — value comparison is NOT performed, so a user-set
  `auto_merge_after_ci: false` survives even when the default is `false`.
- Nested dicts are merged recursively, so a deeply-nested missing sub-key
  (e.g. `plan.phase-6-finalize.auto_rebase_threshold` when `phase-6-finalize`
  exists but the sub-key does not) is added without disturbing siblings.
- Lists are atomic: a present list is kept verbatim; only an absent list key is
  seeded from defaults.
- The merge is idempotent — re-running immediately produces an empty `added[]`.

**Output** (TOON):

```toon
status: success
added[3]:
  - plan.phase-5-execute.per_task_budget_reserve
  - plan.phase-6-finalize.auto_rebase_threshold
  - project.default_base_branch
added_count: 3
```

`added[]` lists the dotted paths of every newly-added key; `added_count` is its
length. An empty `added[]` (with `added_count: 0`) means the live config already
carried every default.

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

# Toggle the phase-5-execute sync-with-main step (default: true)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_on_execute_start --value false

# Select the sync strategy — enum: rebase | merge (default: merge)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_strategy --value rebase
```

**phase-5-execute sync-with-main fields:**

| Field | Type | Default | Semantics |
|-------|------|---------|-----------|
| `rebase_on_execute_start` | bool | `true` | Whether phase-5-execute runs a sync step against `origin/{base_branch}` at phase start. Fast-path no-op when the branch already contains the remote tip. When `false`, phase-6-finalize's `pr update-branch` remains the only sync point. |
| `rebase_strategy` | enum(`rebase`\|`merge`) | `merge` | How the sync step updates the branch. `rebase` rewrites history (requires force-push when a PR is open); `merge` does `git merge --no-edit origin/{base}` (no history rewrite, PR-safe). Invalid values are rejected by the config setter. |

**Symmetric auto-continuation knobs:**

| Field | Phase | Type | Default | Semantics |
|-------|-------|------|---------|-----------|
| `finalize_without_asking` | `phase-5-execute` | bool | `false` | Forward direction. When `true`, after the `5-execute → 6-finalize` transition the orchestrator dispatches `phase-6-finalize` inline rather than halting and prompting the user. |
| `loop_back_without_asking` | `phase-6-finalize` | bool | `false` | Reverse direction. When `true`, a phase-6-finalize step recording `outcome: loop_back` (FIX disposition on a `pr-comment` finding, `pr-comment-overflow` capture, or sonar-roundtrip FIX) re-dispatches the execute pipeline inline, transitions back to `6-finalize`, and re-enters the finalize loop — bounded by `phase-6-finalize.max_iterations` (default 3). When `false` (default), the dispatcher halts and returns control to the user. The two knobs are independent: full unattended execution requires both `true`. See `phase-6-finalize/SKILL.md` Step 3 § "Loop-back continuation hook" for the dispatch shape and the four-corner truth table. |

Each is set with the standard phase-set verb:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field finalize_without_asking --value true

python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set --field loop_back_without_asking --value true
```

### Manage Verification Steps

`set-steps` and `add-step` resolve each step's `order` from its authoritative source (frontmatter on built-in standards docs, frontmatter on project-local `SKILL.md` for `project:` steps, return-dict `order` field for extension-contributed skills) and persist the steps list sorted ascending by that value. They return `error: missing_order` or `error: order_collision` when a step has no declared order or two steps share the same value — fix the offending step's authoritative source.

```bash
# Add a step — the list is re-sorted by resolved order; --position is ignored by the new flow
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute add-step --step sonar_check

# Replace all verification steps (input order is irrelevant — output is sorted by resolved order)
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
| `domain-detect` | `--plan-id [--domain-override]` (deterministic detector for phase-1-init Step 7; walks `request.md` clarified narrative for explicit mentions of configured `skill_domains` and their bundle aliases; returns `domain` + `ambiguous` boolean. Single-domain projects auto-select; multi-match or zero-match returns `ambiguous=true` so the caller raises `AskUserQuestion` — no LLM dispatch fallback applies.) |

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
      "defaults": ["plan-marshall:dev-agent-behavior-rules"],
      "optionals": ["plan-marshall:dev-agent-behavior-rules"],
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
      "rebase_on_execute_start": true,
      "rebase_strategy": "merge",
      "steps": ["quality_check", "build_verify"]
    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 180,
      "loop_back_without_asking": false,
      "steps": [
        "commit_push", "create_pr", "automated_review",
        "sonar_roundtrip", "lessons_capture",
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
| `defaults` | Base skills loaded for all tasks (`plan-marshall:dev-agent-behavior-rules`) |
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

## Canonical invocations

The canonical argparse surface for `manage-config.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-config` Canonical invocations → `effort resolve-target`")
instead of restating the command inline.

### init

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config init \
  [--force]
```

### skill-domains list

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains list
```

### skill-domains get

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get \
  --domain DOMAIN
```

### skill-domains get-defaults

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get-defaults \
  --domain DOMAIN
```

### skill-domains get-optionals

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get-optionals \
  --domain DOMAIN
```

### skill-domains set

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains set \
  --domain DOMAIN [--profile PROFILE] [--defaults LIST] [--optionals LIST]
```

### skill-domains get-extensions

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get-extensions \
  --domain DOMAIN
```

### skill-domains set-extensions

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains set-extensions \
  --domain DOMAIN --type {outline|triage} --skill SKILL_REF
```

### skill-domains add

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains add \
  --domain DOMAIN [--defaults LIST] [--optionals LIST]
```

### skill-domains validate

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains validate \
  --domain DOMAIN --skill SKILL_REF
```

### skill-domains detect

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains detect
```

### skill-domains get-available

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get-available
```

### skill-domains configure

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains configure \
  --domains LIST
```

### skill-domains discover-project

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains discover-project
```

### skill-domains attach-project

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains attach-project \
  --domain DOMAIN --skills LIST
```

### skill-domains active-profiles set

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains active-profiles set \
  --profiles LIST [--domain DOMAIN]
```

### skill-domains active-profiles remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains active-profiles remove \
  [--domain DOMAIN]
```

### system retention get

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config system retention get
```

### system retention set

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config system retention set \
  --field FIELD --value VALUE
```

### plan {phase} get

Applies to every phase sub-noun: `phase-1-init`, `phase-2-refine`, `phase-3-outline`,
`phase-4-plan`, `phase-5-execute`, `phase-6-finalize`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan {phase} get \
  [--field FIELD]
```

### plan {phase} set

Applies to every phase sub-noun (scalar verb).

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan {phase} set \
  --field FIELD --value VALUE
```

### plan phase-5-execute set-max-iterations / plan phase-6-finalize set-max-iterations

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute set-max-iterations \
  --value N
```

### plan phase-5-execute set-steps / plan phase-6-finalize set-steps

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute set-steps \
  --steps LIST
```

### plan phase-5-execute add-step / plan phase-6-finalize add-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute add-step \
  --step STEP_REF
```

### plan phase-5-execute remove-step / plan phase-6-finalize remove-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute remove-step \
  --step STEP_REF
```

### ext-defaults get

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults get \
  --key KEY
```

### ext-defaults set

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults set \
  --key KEY --value VALUE
```

### ext-defaults set-default

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults set-default \
  --key KEY --value VALUE
```

### ext-defaults list

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults list
```

### ext-defaults remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults remove \
  --key KEY
```

### effort read

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort read \
  [--role ROLE] [--phase PHASE] [--default]
```

### effort resolve-target

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort resolve-target \
  [--role ROLE] [--phase PHASE] [--default]
```

### effort apply-preset

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort apply-preset \
  --preset PRESET
```

### resolve-domain-skills

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-domain-skills \
  --domain DOMAIN --profile PROFILE
```

### resolve-workflow-skill-extension

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-workflow-skill-extension \
  --domain DOMAIN --type {outline|triage}
```

### get-skills-by-profile

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config get-skills-by-profile \
  --domain DOMAIN
```

### configure-execute-task-skills

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config configure-execute-task-skills
```

### resolve-execute-task-skill

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-execute-task-skill \
  --profile PROFILE
```

### list-recipes

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes
```

### resolve-recipe

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-recipe \
  --recipe RECIPE_KEY
```

### resolve-outline-skill

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-outline-skill \
  --domain DOMAIN
```

### list-finalize-steps

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```

### list-verify-steps

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```

### domain-detect

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config domain-detect \
  --plan-id PLAN_ID [--domain-override DOMAIN]
```

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
