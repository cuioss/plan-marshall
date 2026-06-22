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
      "per_deliverable_build": [
        "default:verify:compile",
        "default:verify:module-tests"
      ],
      "cost_size_token_table": {
        "S": "25K",
        "M": "60K",
        "L": "130K",
        "XL": "260K"
      },
      "per_envelope_budget_tokens": "400K",
      "verification_steps": [
        "default:verify:quality-gate",
        "default:verify:module-tests",
        "default:verify:coverage"
      ]
    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "checks_wait_timeout_seconds": 600,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "qgate": "auto",
      "steps": [
        "default:commit-push",
        { "default:finalize-step-simplify": { "simplify": "auto" } },
        "default:create-pr",
        { "default:automated-review": { "review_bot_buffer_seconds": 180 } },
        {
          "default:sonar-roundtrip": {
            "touched_file_cleanup": "new_code_only",
            "do_transition": false,
            "ce_wait_timeout_seconds": 600
          }
        },
        "default:lessons-capture",
        {
          "default:branch-cleanup": {
            "pr_merge_strategy": "squash",
            "final_merge_without_asking": false,
            "auto_rebase_threshold": "no_overlap_only"
          }
        },
        "default:record-metrics",
        "default:archive-plan",
        {
          "project:finalize-step-pre-submission-self-review": {
            "self_review": "auto",
            "drop_review_on_scope_gate": false
          }
        }
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
      "optionals": ["plan-marshall:dev-agent-behavior-rules"]
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
- **System domain**: Contains `defaults` and `optionals`
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

Execute phase with integrated verification pipeline. Contains the `commit_and_push` boolean, iteration limits, and a `verification_steps` map for verification. `verification_steps` serializes on disk as the canonical keyed map (a JSON object keyed by step id, `{}` for each config-less verify step — verify steps own no params). Key insertion order is the execution order. The reader consumes the keyed map directly; it is the sole on-disk shape both read and written.

```json
{
  "plan": {
    "phase-5-execute": {
      "commit_and_push": true,
      "max_iterations": 5,
      "per_deliverable_build": [
        "default:verify:compile",
        "default:verify:module-tests"
      ],
      "cost_size_token_table": {
        "S": "25K",
        "M": "60K",
        "L": "130K",
        "XL": "260K"
      },
      "per_envelope_budget_tokens": "400K",
      "verification_steps": {
        "default:verify:quality-gate": {},
        "default:verify:module-tests": {},
        "default:verify:coverage": {}
      }
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `commit_and_push` | bool | true | true=commit per-deliverable + push at finalize; false=local-only run (commit-push/push/PR steps stripped by the manifest `commit_push_disabled` pre-filter) |
| `max_iterations` | int | 5 | Maximum verify-execute-verify loops |
| `per_deliverable_build` | list[string] | `["default:verify:compile","default:verify:module-tests"]` | A list of `default:verify:{canonical}` step IDs — the canonical-verify rungs phase-5-execute runs for the changed module at each per-deliverable chain-tail point (Step 10). The default runs `compile` + the module's scoped `module-tests`. Set to `[]` to disable the focused build (the whole-tree sweep at end-of-phase remains the only build). Each entry must be a `default:verify:{canonical}` ID; the retired enum strings (`off` / `compile-only` / `compile+scoped-test` / `full`) are rejected with a migration error. |
| `cost_size_token_table` | dict | `{"S":"25K","M":"60K","L":"130K","XL":"260K"}` | Size→token table mapping each T-shirt `cost_size` (`S`/`M`/`L`/`XL`) to a predicted-token magnitude. The phase-4-plan bin-packer (`manage-tasks pack-envelopes`) reads it to map a task's derived `cost_size` to its `predicted_cost_tokens`. Keys must be exactly `S`/`M`/`L`/`XL`; each value parses via `sensible_number.parse_sensible_int`. Validated by `validate_cost_size_token_table`. The default magnitudes are calibrated to the forensic 134K–392K per-dispatch range and are tunable to recalibrate the cost model. |
| `per_envelope_budget_tokens` | string | "400K" | Per-envelope packing budget — the token ceiling the phase-4-plan bin-packer accumulates `predicted_cost_tokens` against before opening a new envelope group. Consumed at PLAN time by the bin-packer (`manage-tasks pack-envelopes`), NOT a runtime comparand. The `_tokens` suffix names the unit; the human-friendly value form (`"400K"`) parses to an int via `sensible_number.parse_sensible_int`. The 400K default leaves headroom below a typical context window. |

#### Verify step ID scheme

Both `verification_steps` and `per_deliverable_build` reference verify steps by step ID. There is exactly one parameterized built-in verify step, encoded as `default:verify:{canonical}` — the trailing `{canonical}` segment (e.g. `quality-gate`, `module-tests`, `coverage`, `compile`, `integration-tests`, `e2e`) is the parameter phase-5-execute feeds to `architecture resolve --command {canonical}`. The legacy fixed-name IDs (`default:quality_check` / `default:build_verify` / `default:coverage_check`) are retired. The composer derives the decision-matrix role from the canonical segment (`quality-gate`→quality-gate, `verify`/`module-tests`→module-tests, `coverage`→coverage). See [`phase-5-execute/standards/canonical_verify.md`](../../phase-5-execute/standards/canonical_verify.md) for the parameterized-step contract.

#### Verification Steps

The `verification_steps` field serializes on disk as the canonical keyed map (a JSON object keyed by step id). Verify steps own no params, so every value is an empty `{}` object. Key insertion order is the execution order. The reader consumes the keyed map directly. Two key types:

- **Built-in steps** (`default:verify:{canonical}`): the parameterized canonical-verify step — e.g. `default:verify:quality-gate` (run quality-gate), `default:verify:module-tests` (run full test suite), `default:verify:coverage` (coverage threshold).
- **Project steps** (`project:verify-step-*`): project-local verify-step skills discovered under `.claude/skills/`.

Built-in step keys are always first in the default map; project `verify-step-*` skills follow. The `skill-domains configure` verb seeds the map with the built-in verify steps.

Managed via (the step verbs operate on the keyed map, preserving key insertion order and any existing per-step params):
- `plan phase-5-execute set-steps --steps default:verify:quality-gate,default:verify:module-tests`
- `plan phase-5-execute add-step --step my-bundle:my-verify-step`
- `plan phase-5-execute remove-step --step default:verify:quality-gate`
- `plan phase-5-execute step get --step-id default:verify:quality-gate` (returns the step's complete nested param object in one call)
- `plan phase-5-execute step set --step-id {id} --param {k} --value {v}` (writes one step-owned param into the step's nested object — the compose-time default + wizard global-config write target)
- `plan phase-5-execute set --field per_deliverable_build --value default:verify:compile,default:verify:module-tests` (comma-separated list; empty value disables the focused build)
- `plan phase-5-execute remove-field --field steps` (delete an arbitrary persisted key under the phase section — e.g. removing the legacy `steps` key; see [remove-field](#remove-field) below)

The keyed-map serial form in `marshal.json` is the **compose-time default + wizard global-config write target**. The **plan-local runtime source** is the execution manifest: the composer snapshots each selected step's resolved params into the manifest body at compose time, and phase-5/6 runtime consumers read params via `manage-execution-manifest step-params get` (plan-local, per-plan overridable via `step-params set`), NOT from `marshal.json`. See [manage-execution-manifest/standards/manifest-schema.md](../../manage-execution-manifest/standards/manifest-schema.md) § `step_params`.

#### remove-field

`plan {phase} remove-field --field {key}` deletes an arbitrary scalar/list key from the *persisted* phase section of `marshal.json`. It is available on every phase sub-noun (`phase-1-init` … `phase-6-finalize`).

- Operates on the on-disk section only — NOT the defaults-merged read view. Removing a key the defaults still seed re-exposes the default value on the next `get`; the verb removes an explicit override, it cannot suppress a default.
- Removing a key with no default (e.g. the legacy `plan.phase-5-execute.steps` key left over from before `verification_steps` was introduced) deletes it cleanly.
- Removing a key that is not present in the persisted section returns an error (`Field '{key}' not present in {phase}`) rather than a silent no-op, so callers get an explicit signal.

Example — drop the retired `steps` key from a migrated config:

```
plan phase-5-execute remove-field --field steps
```

### phase-6-finalize

Finalize pipeline with a `steps` keyed map. `steps` serializes on disk as a JSON object keyed by step id: a config-less step maps to `{}`; a param-owning step maps to its nested param object. Step-owned params (`review_bot_buffer_seconds` under `default:automated-review`; `touched_file_cleanup` / `do_transition` / `ce_wait_timeout_seconds` under `default:sonar-roundtrip`; `pr_merge_strategy` / `final_merge_without_asking` / `auto_rebase_threshold` under `default:branch-cleanup`; `simplify` under `default:finalize-step-simplify`; `self_review` / `drop_review_on_scope_gate` under `project:finalize-step-pre-submission-self-review`) nest inside their owning step's value. Key insertion order is the execution order. The reader consumes the keyed map directly; it is the sole on-disk shape both read and written. The one finalize run-at-all gate that has no single owning step body is `qgate` — it stays a flat phase-level sibling, alongside the other ownerless phase-level knobs (`checks_wait_timeout_seconds`, `max_iterations`, the two automation knobs). The opt-in `project:finalize-step-pre-submission-self-review` step is NOT a built-in candidate, so its `self_review` / `drop_review_on_scope_gate` knobs are only stored under the step when a consumer opts the step into `steps`; their defaults (`auto` / `false`) otherwise apply via the consumer's default-merge.

```json
{
  "plan": {
    "phase-6-finalize": {
      "max_iterations": 3,
      "checks_wait_timeout_seconds": 600,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "qgate": "auto",
      "steps": {
        "default:commit-push": {},
        "default:finalize-step-simplify": { "simplify": "auto" },
        "default:create-pr": {},
        "default:automated-review": { "review_bot_buffer_seconds": 180 },
        "default:sonar-roundtrip": {
          "touched_file_cleanup": "new_code_only",
          "do_transition": false,
          "ce_wait_timeout_seconds": 600
        },
        "default:lessons-capture": {},
        "default:branch-cleanup": {
          "pr_merge_strategy": "squash",
          "final_merge_without_asking": false,
          "auto_rebase_threshold": "no_overlap_only"
        },
        "default:record-metrics": {},
        "default:archive-plan": {},
        "project:finalize-step-pre-submission-self-review": {
          "self_review": "auto",
          "drop_review_on_scope_gate": false
        }
      }
    }
  }
}
```

**Flat phase-level fields** (no single owning step):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 3 | Maximum finalize-verify-finalize loops |
| `checks_wait_timeout_seconds` | int | 600 | Default timeout (seconds) for the CI-completion polling commands consumed by `ci_base.py` (`ci checks wait`, `ci pr wait-for-comments`, `ci checks wait-for-status-flip`, and the two `issue wait-for-*` polls). An explicit `--timeout` CLI flag always wins; the 600s fallback covers callers running outside a plan-marshall project. This is a cross-step finalize wait-policy with no single owning step, so it **stays flat** (phase-level). |
| `finalize_without_asking` | bool | true | Forward auto-continuation: auto-continue into finalize after execute completes. `true` (default) skips the gate. |
| `loop_back_without_asking` | bool | false | Reverse auto-continuation: auto-re-enter execute on a `phase-6-finalize` `loop_back` outcome. `false` (default) halts at every loop_back and returns control to the user; `true` opts into the full unattended cycle, capped by `max_iterations`. |
| `qgate` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the finalize blocking-findings re-capture (`pre-push-quality-gate`). **Highest-risk gate** — `never` can mask real build/test failures and push a red tree. The one finalize run-at-all gate that stays flat (it is consumed as a phase-level gate, not a param the owning step body reads). Consumed by `manage-execution-manifest compose`. Validated by `validate_run_at_all`. |
| — (pre-push-quality-gate activation) | derived | — | The `default:pre-push-quality-gate` finalize step's activation is **derived from `build.map`** — no dedicated config key. The manifest composer activates the step when the live footprint touches any `glob` registered in `build.map`; an absent build_map or no footprint match leaves the step inactive. |
| `steps` | dict | (see below) | Keyed map of step references to execute (key insertion order = execution order), persisted sorted ascending by each step's authoritative `order` value. Config-less steps map to `{}`; param-owning steps map to their nested param object. The keyed map is both the internal normalized representation and the on-disk serial form. |

**Step-owned params (nested under their owning step in the `steps` map):**

`default:automated-review`:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `review_bot_buffer_seconds` | int | 180 | Max seconds to wait after CI for new review-bot comments to arrive (used as `--timeout` for `pr wait-for-comments`; the polling subcommand exits as soon as a new comment is posted, so this is a ceiling, not a fixed delay). |
| `re_review_on_loopback` | bool | false | Trigger gate for the post-branch-update re-review. When `true`, a loop-back that advances HEAD re-requests a bot review of the new commits; `false` (default) suppresses the loop-back re-review. |
| `re_review_on_branch_cleanup` | bool | true | Trigger gate for the post-branch-update re-review. When `true` (default), a branch-cleanup operation that advances HEAD (rebase/merge during finalize) re-requests a bot review of the updated branch; `false` suppresses it. |
| `re_review_await_timeout_seconds` | int | 600 | Ceiling (seconds) the step waits for a requested re-review to be submitted by the bot before the `re_review_on_timeout` policy fires. |
| `re_review_on_timeout` | enum(`ask`\|`proceed`\|`defer`) | "ask" | Policy applied when `re_review_await_timeout_seconds` elapses without a submitted bot review. `ask` (default) halts and fires an `AskUserQuestion`; `proceed` advances the unreviewed HEAD to the merge gate (logged at WARNING); `defer` skips the merge for the unreviewed HEAD so finalize is re-entered later. Every branch is decision-logged. |

`default:sonar-roundtrip` (the `sonar_` prefix is dropped within the scoped object):

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `touched_file_cleanup` | enum(`new_code_only`\|`touched_files_zero`) | "new_code_only" | Cleanup-scope for the Sonar roundtrip success criterion. `new_code_only` (default, lean) anchors success on new-code issues == 0; `touched_files_zero` extends the success criterion to also sweep pre-existing issues on the files the plan touched. Consumed by `sonar-roundtrip.md` at the success gate. Validated by `validate_sonar_touched_file_cleanup`. |
| `do_transition` | bool | false | Gate for the server-side SonarCloud dismissal path. `false` (default) routes FALSE-POSITIVE / WON'T-FIX dispositions through in-code suppression (`@SuppressWarnings` / `// NOSONAR`); `true` re-enables the server-side `sonar_rest transition` dismissal. Consumed by triage Step 3c as the fall-through gate for rule classes that cannot be suppressed in-code. |
| `ce_wait_timeout_seconds` | int | 600 | Budget (seconds) for the synchronous in-Python CE-readiness wait performed by `sonar.py fetch-and-store` before enumerating new-code issues — the direct sibling of the flat `checks_wait_timeout_seconds`. An explicit `--ce-wait-timeout` flag overrides it. |

`default:branch-cleanup`:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `pr_merge_strategy` | string | "squash" | squash, merge, rebase — the merge method the branch-cleanup step passes to `pr merge`. |
| `final_merge_without_asking` | bool | false | Whether to merge the PR after CI passes without prompting the operator. `true` merges under the unified `manage-locks:merge_lock` cross-plan mutex (acquired by the branch-cleanup Pre-Merge Gate); `false` (default) prompts the operator before merging. |
| `auto_rebase_threshold` | string | "no_overlap_only" | Gates the pre-merge auto-rebase decision in `branch-cleanup.md`, orthogonal to `final_merge_without_asking`. `no_overlap_only` permits the auto-rebase only when it would touch a disjoint file set; any overlap defers to the operator. |

`default:finalize-step-simplify`:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `simplify` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the holistic post-implementation simplification sweep (`finalize-step-simplify`). `always` forces the step in even when the composer's `simplify_inactive` pre-filter would drop it; `never` removes it; `auto` (the default) defers to that pre-filter. Consumed by `manage-execution-manifest compose`. Validated by `validate_run_at_all`. |

`project:finalize-step-pre-submission-self-review` (the opt-in self-review step; these knobs apply their defaults via the consumer's default-merge when the step is absent from `steps`):

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `self_review` | enum(`auto`\|`always`\|`never`) | auto | Run-at-all gate for the pre-submission structural + cognitive self-review (canonical step `default:pre-submission-self-review`). `always` overrides the manifest composer's `scope_gated_finalize` drop; `never` removes it. Consumed by `manage-execution-manifest compose`. Validated by `validate_run_at_all`. |
| `drop_review_on_scope_gate` | bool | false | Escape hatch for the manifest composer's `scope_gated_finalize` pre-filter. `false` (default) keeps the bot-review invariant intact; `true` opts into additionally dropping `automated-review` on scope-gated (surgical / single_module) plans. The self-review step owns this knob because it is the primary review step the scope gate suppresses. |

**Two-tier source for step params**: the `steps` keyed map in `marshal.json` is the **compose-time default + wizard global-config write target** (read/written via `step get` / `step set`). The **plan-local runtime source** is the execution manifest — the composer snapshots each selected step's resolved params into the manifest body at compose time, and phase-5/6 runtime consumers read params via `manage-execution-manifest step-params get` (plan-local, per-plan overridable via `step-params set`), NOT from `marshal.json`. The execution manifest's `step_params` block is an id-keyed dict — a separate runtime-override surface. See [manage-execution-manifest/standards/manifest-schema.md](../../manage-execution-manifest/standards/manifest-schema.md) § `step_params`.

Managed via (the step verbs operate on the keyed map, preserving key insertion order and existing per-step params):
- `plan phase-6-finalize set-steps --steps default:commit-push,default:create-pr,…`
- `plan phase-6-finalize add-step --step my-bundle:my-finalize-step`
- `plan phase-6-finalize remove-step --step default:sonar-roundtrip`
- `plan phase-6-finalize step get --step-id default:branch-cleanup` (returns the step's complete nested param object in one call)
- `plan phase-6-finalize step set --step-id default:branch-cleanup --param pr_merge_strategy --value rebase` (writes one step-owned param into the step's nested object — the global-config write target)

Default steps: `default:commit-push`, `default:create-pr`, `default:automated-review`, `default:sonar-roundtrip`, `default:lessons-capture`, `default:branch-cleanup`, `default:record-metrics`, `default:archive-plan`. Step types: built-in (`default:` prefix), project (`project:` prefix), skill (fully-qualified `bundle:skill`).

### Run-at-all gates and finalize automation knobs (phase-local)

The lifecycle run-at-all gates are flat phase-local knobs — each owned by the phase whose decision machinery consumes it, tabled under the owning phase section above. There is no top-level policy block: `deep_lane` / `escalation` under `phase-1-init`, `revalidation` under `phase-2-refine`, `qgate` under `phase-3-outline`. Under `phase-6-finalize` only `qgate` stays flat, alongside the two flat automation knobs (`finalize_without_asking` / `loop_back_without_asking`). The two other `phase-6-finalize` run-at-all gates (`simplify`, `self_review`) and the `drop_review_on_scope_gate` escape hatch each own exactly one finalize step, so they are NOT flat — they are step-owned params nested under their owning step in the `steps` map (`simplify` → `default:finalize-step-simplify`; `self_review` / `drop_review_on_scope_gate` → `project:finalize-step-pre-submission-self-review`; `final_merge_without_asking` → `default:branch-cleanup`; see the per-step param sub-tables above). Each gate takes `auto|always|never`, validated by `validate_run_at_all`; the automation knobs are boolean.

The three `phase-6-finalize` run-at-all gates (`self_review` / `qgate` / `simplify`) map one-to-one to finalize steps and are consumed by the manifest composer's finalize selection post-matrix transform — see [`manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md) § "plan.phase-6-finalize Selection" for the gate→step map and the `automated-review` carve-out. `deep_lane` / `escalation` are consumed by the phase-1-init lane router, `revalidation` by the refine revalidation pass, and `phase-3-outline.qgate` by the planning-time Q-Gate dispatch.

**Access shape.** Read/write the flat phase-local knobs (`qgate` and the two automation knobs) via the standard `manage-config plan <phase> get/set --field <knob>` verb; read/write the step-owned knobs (`simplify` / `self_review` / `drop_review_on_scope_gate`) via the `step get/set --step-id <owning-step>` verb. See [`manage-config/SKILL.md`](../SKILL.md) § "Phase-Local Run-at-all Gates and Automation Knobs".

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
