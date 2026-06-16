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
    "working_prefixes": ["feature/", "fix/", "chore/"]
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
      "init_without_asking": true,
      "deep_lane": "auto",
      "escalation": "auto"
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "simplicity": "lean",
      "revalidation": "auto"
    },
    "phase-3-outline": {
      "plan_without_asking": false,
      "qgate": "auto"
    },
    "phase-4-plan": {
      "execute_without_asking": true
    },
    "phase-5-execute": {
      "commit_and_push": true,
      "max_iterations": 5,
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
      "checks_wait_timeout_seconds": 600,
      "auto_rebase_threshold": "no_overlap_only",
      "drop_review_on_scope_gate": false,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "auto_merge_after_ci": true,
      "self_review": "auto",
      "qgate": "auto",
      "simplify": "auto",
      "steps": [
        "default:commit-push", "default:create-pr", "default:automated-review",
        "default:sonar-roundtrip", "default:lessons-capture",
        "default:branch-cleanup", "default:record-metrics", "default:archive-plan"
      ]
    }
  },
  "build": {
    "map": {
      "python": [
        { "glob": "marketplace/targets/*.py", "role": "production", "build_class": "compile" },
        { "glob": "marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/*.py", "role": "production", "build_class": "compile" },
        { "glob": "marketplace/bundles/plan-marshall/skills/manage-config/scripts/*.py", "role": "production", "build_class": "compile" },
        { "glob": "test/plan-marshall/manage-config/*.py", "role": "test", "build_class": "module-tests" }
      ]
    },
    "queue": { "max_slots": 5, "max_retries": 10 }
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

> **`effort` keys** — every phase block may additionally carry an `effort` key (a string level such as `level-3`, or a polymorphic `{default, <role>}` object) that selects the model tier per phase and role. The `effort` resolver and its valid levels are documented separately — see [`../../plan-marshall/standards/effort-variants.md`](../../plan-marshall/standards/effort-variants.md) and the user-facing [efforts page](../../../../../doc/user/efforts.adoc). The `effort` dial is orthogonal to every behavioural field tabled below.

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
    "working_prefixes": ["feature/", "fix/", "chore/"]
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_base_branch` | string | "main" | The project's canonical base branch. `phase-1-init` seeds `references.base_branch` from it; the wizard derives the suggestion from `origin/HEAD`, falling back to `main`. Per-plan overrides via `manage-references set --field base_branch`. |
| `working_prefixes` | list[string] | `["feature/", "fix/", "chore/"]` | The closed set of allowed working-branch prefixes. `manage-status create` validates `--worktree-branch` against this set. The literals live in `constants.py` (`DEFAULT_BRANCH_PREFIX_WORKING`) as the fail-closed fallback. A structural test (`test_branch_prefix_allowlist.py`) asserts every prefix is covered by a `.github/workflows/python-verify.yml` push trigger, so a dropped prefix that would make a PR unmergeable fails CI. |

## Section: skill_domains

Skill configuration per domain. See [skill-domains.md](skill-domains.md) for complete domain structure, profiles, validation rules, and technical domain catalog. See [skill-domains-operations.md](skill-domains-operations.md) for resolution commands and usage patterns.

Key structural summary:
- **System domain**: Contains `defaults`, `optionals`, and `execute_task_skills`
- **Technical domains**: Reference a `bundle` and declare `workflow_skill_extensions` (outline, triage)
- **Profiles**: Loaded at runtime from `extension.py`, not stored in marshal.json

## Section: build.map

The file-to-build contract: a domain-keyed inventory of `{glob, role, build_class}` entries that maps every changed path to the build action it requires. The build map lives at the top-level `build.map` block (its owning block, peer to `build.queue`) and is the persisted, user-adaptable layer of the contract; the deterministic deriver (`architecture derive-verification`) reads the effective map to emit a task's verification command set.

### Source, applicability scoping, write-once semantics, and fail-closed read

`build_map` is **seeded from the domain extensions**, not hand-authored, and its globs are **explicit `(pattern, role)` routes**, not author-guessed literals. Each registered extension's `classify_globs()` declares those routes directly — a concrete glob pattern paired with one of the three resolved roles (see [extension-contract.md](../../extension-api/standards/extension-contract.md) § `classify_globs`); the aggregator collects them verbatim via the `script-shared` route collector. `classify_build_class(glob, role)` then stamps each route with its canonical-named `build_class`; the aggregator collects these into the `{domain: [{glob, role, build_class}]}` structure. Patterns use single-`*` fnmatch globs (never recursive `**`): because `fnmatch` lets a single `*` span `/`, a compact route like `marketplace/bundles/*.py` covers every nested `.py` under `marketplace/bundles/` — including each `marketplace/bundles/<bundle>/skills/plan-marshall-plugin/extension.py` — and `marketplace/targets/*.py` covers `marketplace/targets/generate.py` and any file beneath `targets/`. A bare config-file basename route (no `/` — e.g. `pom.xml`, `package.json`, `tsconfig.json`) is matched by basename anywhere in the tree, so a config file that lives only in subdirectories is kept in the seed and matched at build-decision time, not only a repo-root instance. Completeness is enforced by a separate **git-tracked completeness validator**: it scans `git ls-files` and flags any tracked source file (suffix `.py`) no declared `production`/`test` route covers, so a forgotten production module surfaces as an uncovered path while untracked `target/` / `.venv/` output is never flagged. The predicates stay in extension Python — they are **not** migrated into config; `build_map` is the seeded snapshot of the collected routes.

**Applicability scoping.** `aggregate_build_map()` includes a domain's routes only when that domain applies to the project. It consults each domain's owning extension's `applies_to_module()` against the discovered project modules (`discover_project_modules`, keyed off the tracked-config parent) and keeps the domain's routes only when `applies_to_module()` reports `applicable: True` for at least one discovered module — the same applicability predicate architecture enrichment uses. A Python-only project therefore never receives `java` / `oci` / `javascript` routes merely because those bundles are installed. Because applicability is resolved against discovered modules, the seed is **post-architecture-only**: when module discovery yields no modules (architecture not yet discovered) the aggregation is empty. Each `applies_to_module()` call is defended so a single misbehaving extension cannot crash the seed.

Seeding is **write-once**: an existing `build.map` block is never clobbered by a default re-seed, so a correction made directly to the seeded block survives. The build map is **not** seeded at `init` or by `sync-defaults` — `get_default_config()` does not include a `build.map` block. The wizard's Step 8b (`build-map seed`, run after architecture discovery so applicability scoping has discovered modules) is the **sole authoritative seed point**; the write-once guard makes that first explicit seed authoritative. Re-seed (preserving the existing seed) via `build-map seed`; force a clean re-derivation that discards the existing block via `build-map seed --force`; read the effective map via `build-map read`. The read **fails closed**: when `build.map` is absent the read returns a structured error rather than an empty map, so a missing seed surfaces instead of silently yielding a no-build. There is no separate override layer; corrections are made directly to the seeded entries.

### Structure

```json
{
  "build": {
    "map": {
      "python": [
        { "glob": "marketplace/targets/*.py", "role": "production", "build_class": "compile" },
        { "glob": "marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/*.py", "role": "production", "build_class": "compile" },
        { "glob": "marketplace/bundles/plan-marshall/skills/manage-config/scripts/*.py", "role": "production", "build_class": "compile" },
        { "glob": "test/plan-marshall/manage-config/*.py", "role": "test", "build_class": "module-tests" }
      ]
    }
  }
}
```

The `python`-domain globs above are a representative sample — the real seed carries the compact `(pattern, role)` routes each extension's `classify_globs()` declares (e.g. `build.py`, `marketplace/bundles/*.py`, `marketplace/targets/*.py`, `test/*.py`), each stamped with its `build_class`. Single-`*` fnmatch patterns span `/`, so a handful of routes cover files in nested directories, and a bare config-file basename route matches the file at any tree depth; the git-tracked completeness validator confirms none is left uncovered.

### Fields (per entry)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `glob` | string | Yes | The path glob the entry classifies. Precedence is **longest-glob-wins** (the existing aggregator specificity): when two entries match a path, the more specific glob claims it. |
| `role` | string | Yes | File role — one of `production`, `test`, `config`. |
| `build_class` | string | Yes | The deterministic build action for the `(glob, role)` pair — one of the closed four-value enum below. |

### build_class enum

Closed four-value set, **named for the canonical command directly** — the `build_class` value IS the canonical command name, with no name-to-name indirection map. The single source of truth is `BUILD_CLASSES` in `script-shared`'s extension constants, shared by `ExtensionBase.classify_build_class()`, the domain extensions, and their tests.

| `build_class` | Role it attaches to | Derived verification |
|---------------|---------------------|----------------------|
| `compile` | production | `compile` for the changed module |
| `module-tests` | test | `test-compile` + `module-tests` for the changed module |
| `verify` | config | `verify` (full reactor for the changed module) |
| `none` | any | No command — a changed set whose only role yields `none` derives no build |

Managed via:
- `build-map seed` (re-seed `build.map` from applicable extensions — write-once)
- `build-map seed --force` (clear any existing block and re-derive a clean one — bypasses the write-once guard)
- `build-map read` (return the effective map from `build.map`; fail-closed when absent)

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
      "init_without_asking": true,
      "deep_lane": "auto",
      "escalation": "auto"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `branch_strategy` | string | "feature" | direct, feature |
| `use_worktree` | bool | true | Whether the plan allocates an isolated worktree. `true` (default, with `branch_strategy: feature`) materialises a worktree at `.plan/local/worktrees/{plan-id}/` during `phase-5-execute` Step 2.5; `false` runs against the main checkout. |
| `init_without_asking` | bool | true | Auto-continue from `phase-1-init` to `phase-2-refine`. `true` (default) skips the gate; `false` stops after init and waits for the user. |
| `deep_lane` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the precondition-driven deep planning lane. Consumed by the phase-1-init `planning-lane route`. `always` forces deep; `never` forces light (the DQ3 hard-escalation ratchet still fires unless `escalation` is also `never`); `auto` defers to the DQ1 signal set. Validated by `validate_run_at_all`. |
| `escalation` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the hard-escalation safety ratchet (DQ3 explosion / build-break / premise). `auto` keeps it live; `never` is the explicit full-speed-full-risk opt-in. Validated by `validate_run_at_all`. |

### phase-2-refine

```json
{
  "plan": {
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "simplicity": "lean",
      "revalidation": "auto"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `confidence_threshold` | int | 95 | Confidence threshold for refinement completion |
| `compatibility` | string | "breaking" | breaking, deprecation, smart_and_ask |
| `simplicity` | string | "lean" | lean, pragmatic, defensive — how aggressively the implementation favours the minimum viable surface over speculative structure. `lean` (default) implements the strict minimum; `pragmatic` keeps low-risk structure that aids readability; `defensive` retains belt-and-suspenders guards/seams where uncertain. |
| `revalidation` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the premise / narrative-vs-code safety check (light lane + deep refine). `never` disables the safety check. Validated by `validate_run_at_all`. |

### phase-3-outline

```json
{
  "plan": {
    "phase-3-outline": {
      "plan_without_asking": false,
      "qgate": "auto"
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `plan_without_asking` | bool | false | Auto-proceed from outline to task creation without user review |
| `qgate` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the planning-time Q-Gate validation (deep-lane outline dispatch). Validated by `validate_run_at_all`. |

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

Execute phase with integrated verification pipeline. Contains the `commit_and_push` boolean, iteration limits, and a flat ordered `steps` list for verification.

```json
{
  "plan": {
    "phase-5-execute": {
      "commit_and_push": true,
      "max_iterations": 5,
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
| `commit_and_push` | bool | true | true=commit per-deliverable + push at finalize; false=local-only run (commit-push/push/PR steps stripped by the manifest `commit_push_disabled` pre-filter) |
| `max_iterations` | int | 5 | Maximum verify-execute-verify loops |
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
      "checks_wait_timeout_seconds": 600,
      "auto_rebase_threshold": "no_overlap_only",
      "drop_review_on_scope_gate": false,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "auto_merge_after_ci": true,
      "self_review": "auto",
      "qgate": "auto",
      "simplify": "auto",
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
| `checks_wait_timeout_seconds` | int | 600 | Default timeout (seconds) for the CI-completion polling commands consumed by `ci_base.py` (`ci checks wait`, `ci pr wait-for-comments`, `ci checks wait-for-status-flip`, and the two `issue wait-for-*` polls). An explicit `--timeout` CLI flag always wins; the 600s fallback covers callers running outside a plan-marshall project. This is a finalize wait-policy, owned by phase-6-finalize. |
| `auto_rebase_threshold` | string | "no_overlap_only" | Gates the pre-merge auto-rebase decision in `branch-cleanup.md`, orthogonal to `auto_merge_after_ci`. `no_overlap_only` permits the auto-rebase only when it would touch a disjoint file set; any overlap defers to the operator. |
| `drop_review_on_scope_gate` | bool | false | Escape hatch for the manifest composer's `scope_gated_finalize` pre-filter. `false` (default) keeps the bot-review invariant intact; `true` opts into additionally dropping `automated-review` on scope-gated plans. |
| `finalize_without_asking` | bool | true | Forward auto-continuation: auto-continue into finalize after execute completes. `true` (default) skips the gate. |
| `loop_back_without_asking` | bool | false | Reverse auto-continuation: auto-re-enter execute on a `phase-6-finalize` `loop_back` outcome. `false` (default) halts at every loop_back and returns control to the user; `true` opts into the full unattended cycle, capped by `max_iterations`. |
| `auto_merge_after_ci` | bool | true | Whether to merge automatically once CI passes. `true` (default) merges under the unified `manage-locks:merge_lock` cross-plan mutex (acquired by the branch-cleanup Pre-Merge Gate); `false` prompts the operator before merging. |
| `self_review` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the pre-submission structural + cognitive self-review (`finalize-step-pre-submission-self-review`). `always` overrides the manifest composer's `scope_gated_finalize` drop; `never` removes it. Consumed by `manage-execution-manifest compose`. Validated by `validate_run_at_all`. |
| `qgate` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the finalize blocking-findings re-capture (`pre-push-quality-gate`). **Highest-risk gate** — `never` can mask real build/test failures and push a red tree. Consumed by `manage-execution-manifest compose`. Validated by `validate_run_at_all`. |
| `simplify` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the holistic post-implementation simplification sweep (`finalize-step-simplify`). `always` forces the step in even when the composer's `simplify_inactive` pre-filter would drop it; `never` removes it; `auto` (the default) defers to that pre-filter. Consumed by `manage-execution-manifest compose`. Validated by `validate_run_at_all`. |
| — (pre-push-quality-gate activation) | derived | — | The `default:pre-push-quality-gate` finalize step's activation is **derived from `build.map`** — no dedicated config key. The manifest composer activates the step when the live footprint touches any `glob` registered in `build.map`; an absent build_map or no footprint match leaves the step inactive. |
| `steps` | list | (see below) | Ordered list of step references to execute — persisted sorted ascending by each step's authoritative `order` value |

Default steps: `default:commit-push`, `default:create-pr`, `default:automated-review`, `default:sonar-roundtrip`, `default:lessons-capture`, `default:branch-cleanup`, `default:record-metrics`, `default:archive-plan`. Step types: built-in (`default:` prefix), project (`project:` prefix), skill (fully-qualified `bundle:skill`).

### Run-at-all gates and finalize automation knobs (phase-local)

The lifecycle run-at-all gates and finalize automation knobs are flat phase-local knobs — each owned by the phase whose decision machinery consumes it, tabled under the owning phase section above. There is no top-level policy block: `deep_lane` / `escalation` under `phase-1-init`, `revalidation` under `phase-2-refine`, `qgate` under `phase-3-outline`, and `self_review` / `qgate` / `simplify` plus the three automation knobs (`finalize_without_asking` / `loop_back_without_asking` / `auto_merge_after_ci`) under `phase-6-finalize`. Each gate takes `auto|always|never`, validated by `validate_run_at_all`; the automation knobs are boolean.

The four `phase-6-finalize` gates map one-to-one to finalize steps and are consumed by the manifest composer's finalize selection post-matrix transform — see [`manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md) § "plan.phase-6-finalize Selection" for the gate→step map and the `automated-review` carve-out. `deep_lane` / `escalation` are consumed by the phase-1-init lane router, `revalidation` by the refine revalidation pass, and `phase-3-outline.qgate` by the planning-time Q-Gate dispatch.

**Access shape.** Read/write each knob via the standard `manage-config plan <phase> get/set --field <knob>` verb. See [`manage-config/SKILL.md`](../SKILL.md) § "Phase-Local Run-at-all Gates and Automation Knobs".

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

## CI Provider Resolution

There is no top-level `ci` block. The CI provider is resolved from the `providers[]` array (the entry whose `category == 'ci'`, mapping `plan-marshall:workflow-integration-github` → `github` and `plan-marshall:workflow-integration-gitlab` → `gitlab`). The CI-completion polling timeout lives under `plan.phase-6-finalize.checks_wait_timeout_seconds` (a finalize wait-policy — see § `phase-6-finalize`). Tool availability is verified live via `plan-marshall:tools-integration-ci:ci_health verify-all` — it is not persisted, since tool/auth status varies per developer machine and is cheap to check on demand.

## Default Values

Default values are defined in:

```
plan-marshall/skills/manage-config/scripts/_config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
