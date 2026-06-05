# Data Model

JSON structure and field definitions for project configuration.

## File Location

`.plan/marshal.json`

## Complete Structure

```json
{
  "providers": [
    {
      "skill_name": "plan-marshall:workflow-integration-github",
      "category": "ci",
      "verify_command": "gh auth status",
      "description": "GitHub CI provider via gh CLI",
      "url": "https://api.github.com"
    }
  ],
  "project": {
    "default_base_branch": "main",
    "branch_naming": {
      "working_prefixes": ["feature/", "fix/", "chore/"],
      "ci_allowlist": ["main", "feature/*", "fix/*", "chore/*", "dependabot/**"]
    }
  },
  "ci": {
    "repo_url": "https://github.com/org/repo",
    "provider": "github",
    "detected_at": "2025-01-15T10:30:00Z",
    "sonar_project": null,
    "checks_wait_timeout_seconds": 600
  },
  "plan": {
    "open_in_ide": true,
    "coverage": {
      "thoroughness": "inherit",
      "scope": "inherit"
    },
    "phase-1-init": {
      "branch_strategy": "feature",
      "use_worktree": true,
      "init_without_asking": true
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "simplicity": "lean"
    },
    "phase-3-outline": {
      "plan_without_asking": false
    },
    "phase-4-plan": {
      "execute_without_asking": true
    },
    "phase-5-execute": {
      "commit_strategy": "per_plan",
      "finalize_without_asking": true,
      "verification_max_iterations": 5,
      "per_deliverable_build": "compile+scoped-test",
      "per_task_budget_reserve_tokens": "50K",
      "steps": [
        "default:quality_check",
        "default:build_verify",
        "default:coverage_check"
      ]
    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 180,
      "pr_merge_strategy": "squash",
      "loop_back_without_asking": false,
      "auto_merge_after_ci": true,
      "auto_rebase_threshold": "no_overlap_only",
      "lightweight_track_override": false,
      "pre_push_quality_gate": {
        "activation_globs": []
      },
      "steps": [
        "default:commit-push", "default:create-pr", "default:automated-review",
        "default:sonar-roundtrip", "default:lessons-capture",
        "default:branch-cleanup", "default:record-metrics", "default:archive-plan"
      ]
    }
  },
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
      "lessons_superseded_days": 0,
      "temp_on_maintenance": true
    }
  }
}
```

> **`effort` keys** — every phase block may additionally carry an `effort` key (a string level such as `high`, or a polymorphic `{default, <role>}` object) that selects the model tier per phase and role. The `effort` resolver and its valid levels are documented separately — see [`../../plan-marshall/standards/effort-variants.md`](../../plan-marshall/standards/effort-variants.md) and the user-facing [efforts page](../../../../../doc/user/efforts.adoc). The `effort` dial is orthogonal to every behavioural field tabled below.

## Section: providers

A top-level JSON array registering the external tool providers (CI, version-control, …) the project depends on. Each entry is verified live by `manage-providers`; the array seeds with an empty list on `init` and is populated by provider registration.

### Fields (per array entry)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_name` | string | Yes | Fully-qualified `bundle:skill` reference to the provider integration skill (e.g. `plan-marshall:workflow-integration-github`) |
| `category` | string | Yes | Provider category — `ci`, `version-control`, … |
| `verify_command` | string | Yes | Shell command run to verify the provider is authenticated/available (e.g. `gh auth status`) |
| `description` | string | No | Human-readable description of the provider |
| `url` | string | No | Provider endpoint or repo URL |

## Section: project

Project-level settings (committed, shared via git). Seeded on `init` and back-filled into existing projects by `sync-defaults`.

### Structure

```json
{
  "project": {
    "default_base_branch": "main",
    "branch_naming": {
      "working_prefixes": ["feature/", "fix/", "chore/"],
      "ci_allowlist": ["main", "feature/*", "fix/*", "chore/*", "dependabot/**"]
    }
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_base_branch` | string | "main" | The project's canonical base branch. `phase-1-init` seeds `references.base_branch` from it; the wizard derives the suggestion from `origin/HEAD`, falling back to `main`. Per-plan overrides via `manage-references set --field base_branch`. |
| `branch_naming.working_prefixes` | list[string] | `["feature/", "fix/", "chore/"]` | The closed set of allowed working-branch prefixes. `manage-status create` validates `--worktree-branch` against this set. The literals live in `constants.py` (`DEFAULT_BRANCH_PREFIX_WORKING`) as the fail-closed fallback. |
| `branch_naming.ci_allowlist` | list[string] | `["main", "feature/*", "fix/*", "chore/*", "dependabot/**"]` | The CI push-trigger allowlist (glob form), pinned by a structural test against `.github/workflows/python-verify.yml`. Source-of-truth literals in `constants.py` (`DEFAULT_CI_BRANCH_ALLOWLIST`). |

## Section: skill_domains

Skill configuration per domain. See [skill-domains.md](skill-domains.md) for complete domain structure, profiles, validation rules, and technical domain catalog. See [skill-domains-operations.md](skill-domains-operations.md) for resolution commands and usage patterns.

Key structural summary:
- **System domain**: Contains `defaults`, `optionals`, and `execute_task_skills`
- **Technical domains**: Reference a `bundle` and declare `workflow_skill_extensions` (outline, triage)
- **Profiles**: Loaded at runtime from `extension.py`, not stored in marshal.json

## Section: system

System-level infrastructure settings.

### Structure

```json
{
  "system": {
    "retention": {
      "logs_days": 1,
      "archived_plans_days": 5,
      "lessons_superseded_days": 0,
      "temp_on_maintenance": true
    }
  }
}
```

### Retention Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `logs_days` | int | 1 | Days to keep execution logs |
| `archived_plans_days` | int | 5 | Days to keep archived plans |
| `lessons_superseded_days` | int | 0 | Days to keep superseded lessons before removal (`0` = remove immediately on the next maintenance pass) |
| `temp_on_maintenance` | bool | true | Clean temp on maintenance |

## Section: plan

Phase-specific configuration for the 6-phase workflow model. Each phase with configurable settings has its own sub-section.

> **Phase naming**: JSON keys use the `phase-{N}-{name}` prefix form (e.g., `phase-1-init`). The canonical phase name is `1-init` — see [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the standard phase list.

### Plan-level (non-phase) fields

These fields live directly under `plan`, outside any phase block.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `open_in_ide` | bool | true | Whether Plan Marshall attempts to open the plan/worktree in the IDE on creation. A missing key is also treated as `true` by `manage-files open-in-ide`. Set `false` to suppress IDE auto-open. |

(The plan-wide `plan.coverage` two-dial cell is documented under [Coverage cell](#coverage-cell-per-phase--plan-wide) below.)

### phase-1-init

```json
{
  "plan": {
    "phase-1-init": {
      "branch_strategy": "feature",
      "use_worktree": true,
      "init_without_asking": true
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `branch_strategy` | string | "feature" | direct, feature |
| `use_worktree` | bool | true | Whether the plan allocates an isolated worktree. `true` (default, with `branch_strategy: feature`) materialises a worktree at `.plan/local/worktrees/{plan-id}/` during `phase-5-execute` Step 2.5; `false` runs against the main checkout. |
| `init_without_asking` | bool | true | Auto-continue from `phase-1-init` to `phase-2-refine`. `true` (default) skips the gate; `false` stops after init and waits for the user. |

### phase-2-refine

```json
{
  "plan": {
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "simplicity": "lean"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `confidence_threshold` | int | 95 | Confidence threshold for refinement completion |
| `compatibility` | string | "breaking" | breaking, deprecation, smart_and_ask |
| `simplicity` | string | "lean" | lean, pragmatic, defensive — how aggressively the implementation favours the minimum viable surface over speculative structure. `lean` (default) implements the strict minimum; `pragmatic` keeps low-risk structure that aids readability; `defensive` retains belt-and-suspenders guards/seams where uncertain. |

### phase-3-outline

```json
{
  "plan": {
    "phase-3-outline": {
      "plan_without_asking": false
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `plan_without_asking` | bool | false | Auto-proceed from outline to task creation without user review |

### phase-4-plan

```json
{
  "plan": {
    "phase-4-plan": {
      "execute_without_asking": true
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `execute_without_asking` | bool | true | Auto-continue to execute phase after task creation |

### phase-5-execute

Execute phase with integrated verification pipeline. Contains commit strategy, iteration limits, and a flat ordered `steps` list for verification.

```json
{
  "plan": {
    "phase-5-execute": {
      "commit_strategy": "per_plan",
      "finalize_without_asking": true,
      "verification_max_iterations": 5,
      "per_deliverable_build": "compile+scoped-test",
      "per_task_budget_reserve_tokens": "50K",
      "steps": [
        "default:quality_check",
        "default:build_verify",
        "default:coverage_check"
      ]
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `commit_strategy` | string | "per_plan" | per_deliverable, per_plan, none — when the execute loop commits (each deliverable chain-tail / once at end of phase / defer to finalize) |
| `finalize_without_asking` | bool | true | Auto-continue to finalize phase after execute completes |
| `verification_max_iterations` | int | 5 | Maximum verify-execute-verify loops |
| `per_deliverable_build` | string | "compile+scoped-test" | off, compile-only, compile+scoped-test, full — build depth at each per-deliverable chain-tail point (Step 10). `off` skips the focused build; `compile-only` type-checks the changed module; `compile+scoped-test` adds the module's scoped tests; `full` runs a whole-tree quality-gate per deliverable (legacy, opt-in). |
| `per_task_budget_reserve_tokens` | string | "50K" | Per-task budget **reserve** — the minimum context-window margin that must remain free before the budget-bounded task loop starts another task. Governs the continue-vs-yield sentinel. The `_tokens` suffix names the unit; the human-friendly value form (`"50K"`) is parsed to an int by `sensible_number.parse_sensible_int` in the phase-5-execute consumer. The workflow's documented fallback when the key is absent is `50000`. |

#### Verification Steps

The `steps` list contains an ordered sequence of verification step references. Two types:

- **Built-in steps** (no colon): `quality_check` (run quality-gate), `build_verify` (run full test suite)
- **Extension steps** (colon notation): Fully-qualified skill references from domain bundles (e.g., `my-bundle:my-verify-step`)

Built-in steps are always first in the default list. Extension steps are appended by `skill-domains configure` from `provides_verify_steps()` in each domain's `extension.py`. See [extension-contract.md](../../extension-api/standards/extension-contract.md) for the complete contract.

Managed via:
- `plan phase-5-execute set-steps --steps quality_check,build_verify`
- `plan phase-5-execute add-step --step my-bundle:my-verify-step`
- `plan phase-5-execute remove-step --step quality_check`

### phase-6-finalize

Finalize pipeline with numbered boolean steps.

```json
{
  "plan": {
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 180,
      "pr_merge_strategy": "squash",
      "loop_back_without_asking": false,
      "auto_merge_after_ci": true,
      "auto_rebase_threshold": "no_overlap_only",
      "lightweight_track_override": false,
      "pre_push_quality_gate": {
        "activation_globs": []
      },
      "steps": [
        "default:commit-push", "default:create-pr", "default:automated-review",
        "default:sonar-roundtrip", "default:lessons-capture",
        "default:branch-cleanup", "default:record-metrics", "default:archive-plan"
      ]
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 3 | Maximum finalize-verify-finalize loops |
| `review_bot_buffer_seconds` | int | 180 | Max seconds to wait after CI for new review-bot comments to arrive (used as `--timeout` for `pr wait-for-comments`; the polling subcommand exits as soon as a new comment is posted, so this is a ceiling, not a fixed delay) |
| `pr_merge_strategy` | string | "squash" | squash, merge, rebase — the merge method the branch-cleanup step passes to `pr merge` |
| `loop_back_without_asking` | bool | false | Auto-continue from a `phase-6-finalize` `loop_back` outcome back into `phase-5-execute`. `false` (default) halts at every loop_back and returns control to the user; `true` opts into the full unattended cycle, capped by `max_iterations`. |
| `auto_merge_after_ci` | bool | true | Whether to merge automatically once CI passes. `true` (default) merges via the cross-plan merge-lock; `false` prompts the operator before merging. Plain boolean — not tri-state. |
| `auto_rebase_threshold` | string | "no_overlap_only" | Gates the pre-merge auto-rebase decision in `branch-cleanup.md`, orthogonal to `auto_merge_after_ci`. `no_overlap_only` permits the auto-rebase only when it would touch a disjoint file set; any overlap defers to the operator. |
| `lightweight_track_override` | bool | false | Escape hatch for the manifest composer's `scope_gated_finalize` pre-filter. `false` (default) keeps the bot-review invariant intact; `true` opts into additionally dropping `automated-review` on scope-gated plans. |
| `pre_push_quality_gate.activation_globs` | list[string] | `[]` | Glob list the manifest composer reads to decide whether the `default:pre-push-quality-gate` finalize step is active. An empty list (default) leaves the step inactive. |
| `steps` | list | (see below) | Ordered list of step references to execute — persisted sorted ascending by each step's authoritative `order` value |

Default steps: `default:commit-push`, `default:create-pr`, `default:automated-review`, `default:sonar-roundtrip`, `default:lessons-capture`, `default:branch-cleanup`, `default:record-metrics`, `default:archive-plan`. Step types: built-in (`default:` prefix), project (`project:` prefix), skill (fully-qualified `bundle:skill`).

### Coverage cell (per-phase + plan-wide)

Coverage is a two-dial contract — `thoroughness` (T1–T5) × `scope` (change-set…overall) — orthogonal to the `effort` dial (model tier). A per-phase override lives under the phase entry's `coverage` key; the plan-wide fallback is a single `plan.coverage` object. The resolver walks `plan.<phase>.coverage.<field>` → `plan.coverage.<field>` → `inherit` for each field independently, mirroring the `effort` resolver's polymorphic walk applied per-field.

```json
{
  "plan": {
    "coverage": {
      "thoroughness": "T2",
      "scope": "module"
    },
    "phase-5-execute": {
      "coverage": {
        "thoroughness": "T4",
        "scope": "component"
      }
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `thoroughness` | string | "inherit" | T1, T2, T3, T4, T5, inherit |
| `scope` | string | "inherit" | change-set, artifact, component, module, overall, inherit |

**Coupling constraint** — `reject thoroughness ≥ T4 ∧ scope < component`. A relation-tracing thoroughness (T4/T5) cannot be honoured below `component` scope because the siblings the relations point at are out of radius. The constraint is enforced at lookup time (from both `coverage read` and `coverage resolve`) with `error_type: coverage_coupling_violation`. An `inherit` on either field is unconstrained. The constraint is defined verbatim in [`dev-agent-behavior-rules/standards/thoroughness.md`](../../dev-agent-behavior-rules/standards/thoroughness.md) § Coupling Constraint.

`plan.coverage` is the project-default knob (seeded `inherit/inherit`); the `read`/`resolve` verbs read `marshal.json` only (no per-plan tier). The per-invocation user-gathered identifier + expanded instruction live in `status.json` metadata per the [coverage-gathering contract](../../dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — the components that implement that contract are coverage's consumers. `coverage resolve` is the project-default tier those components fall back to when no per-invocation cell was gathered.

Resolved via:
- `coverage read --phase phase-5-execute` (resolve a phase's cell, project default)
- `coverage resolve --phase phase-5-execute` (resolve cell + coupling result, project default)
- `coverage read --default` (raw `plan.coverage` lookup)
- `coverage expand --thoroughness T3 --scope component` (static identifier → contract instruction block; `inherit/inherit` → behavior-preserving instruction)

## Section: ci

CI provider configuration (project-level, shared via git).

### Structure

```json
{
  "ci": {
    "repo_url": "https://github.com/org/repo",
    "provider": "github",
    "detected_at": "2025-01-15T10:30:00Z",
    "sonar_project": "my-project-key",
    "checks_wait_timeout_seconds": 600
  }
}
```

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_url` | string | No | - | Git remote origin URL |
| `provider` | string | Yes | - | CI provider: `github`, `gitlab`, `unknown` |
| `detected_at` | string | No | - | ISO timestamp of last detection |
| `sonar_project` | string | No | null | SonarQube/Cloud project key |
| `checks_wait_timeout_seconds` | int | No | 600 | Default timeout (seconds) for the CI polling commands that wait for run completion (`ci checks wait`, `ci pr wait-for-comments`, …). An explicit `--timeout` CLI flag always wins; the 600s fallback covers callers running outside a plan-marshall project. |

### Provider Values

| Value | CLI Tool | Description |
|-------|----------|-------------|
| `github` | `gh` | GitHub (github.com or enterprise) |
| `gitlab` | `glab` | GitLab (gitlab.com or self-hosted) |
| `unknown` | - | Could not detect provider |

### Note: Authenticated Tools

Tool availability is verified live via `plan-marshall:tools-integration-ci:ci_health verify-all` — it is not persisted, since tool/auth status varies per developer machine and is cheap to check on demand.

## Default Values

Default values are defined in:

```
plan-marshall/skills/manage-config/scripts/_config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
