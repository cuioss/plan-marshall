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
    "working_prefixes": ["feature/", "fix/", "chore/"],
    "pr_strategy": "compact",
    "pr_compact_max_changed_files": 150,
    "merge_queue_managed_externally": false
  },
  "plan": {
    "open_in_ide": true,
    "finding_raw_input_max_bytes": 65536,
    "coverage": {
      "thoroughness": "inherit",
      "scope": "inherit"
    },
    "phase-1-init": {
      "branch_strategy": "feature",
      "use_worktree": true,
      "init_without_asking": true,
      "deep_lane": "auto",
      "escalation": "auto",
      "lane_selection": "ask",
      "lane_prune_thresholds": {
        "confidence_complete": 95,
        "linear_change_max_deliverables": 1
      }
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "simplicity": "lean",
      "revalidation": "auto"
    },
    "phase-3-outline": {
      "plan_without_asking": false,
      "q_gate_validation": "once"
    },
    "phase-4-plan": {
      "execute_without_asking": true,
      "q_gate_validation": "once"
    },
    "phase-5-execute": {
      "commit_and_push": true,
      "max_iterations": 5,
      "per_deliverable_build": [
        "default:verify:compile",
        "default:verify:module-tests"
      ],
      "cost_size_token_table": {
        "XS": "5K",
        "S": "25K",
        "M": "60K",
        "L": "130K",
        "XL": "260K",
        "XXL": "520K"
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
      "steps": {
        "default:pre-submission-self-review": {
          "drop_review_on_scope_gate": false
        },
        "default:finalize-step-simplify": {},
        "default:push": {},
        "default:create-pr": {},
        "plan-marshall:automatic-review": {
          "review_bot_buffer_seconds": 180,
          "lane": "ask"
        },
        "default:sonar-roundtrip": {
          "touched_file_cleanup": "new_code_only",
          "do_transition": false,
          "ce_wait_timeout_seconds": 600,
          "lane": "ask"
        },
        "default:lessons-capture": {},
        "default:branch-cleanup": {
          "pr_merge_strategy": "squash",
          "final_merge_without_asking": false,
          "auto_rebase_threshold": "no_overlap_only"
        },
        "default:record-metrics": {},
        "default:archive-plan": {}
      }
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
  "credentials_config": {
    "plan-marshall:workflow-integration-sonar": {
      "organization": "cuioss",
      "project_key": "cuioss_plan-marshall"
    }
  },
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:persona-plan-marshall-agent"],
      "optionals": ["plan-marshall:persona-plan-marshall-agent"]
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

> **`effort` keys** — every phase block may additionally carry an `effort` key (a string level such as `level-3`, or a polymorphic `{default, <role>}` object) that selects the model tier per phase and role. The `effort` resolver and its valid levels are documented separately — see [`../../plan-marshall/standards/effort-variants.md`](../../plan-marshall/standards/effort-variants.md) and the user-facing [efforts page](../../../../../../doc/user/efforts.adoc). The `effort` dial is orthogonal to every behavioural field tabled below.

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
    "working_prefixes": ["feature/", "fix/", "chore/"],
    "pr_strategy": "compact",
    "pr_compact_max_changed_files": 150,
    "merge_queue_managed_externally": false
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_base_branch` | string | "main" | The project's canonical base branch. `phase-1-init` seeds `references.base_branch` from it; the wizard derives the suggestion from `origin/HEAD`, falling back to `main`. Per-plan overrides via `manage-references set --field base_branch`. |
| `working_prefixes` | list[string] | `["feature/", "fix/", "chore/"]` | The closed set of allowed working-branch prefixes. `manage-status create` validates `--worktree-branch` against this set. The literals live in `constants.py` (`DEFAULT_BRANCH_PREFIX_WORKING`) as the fail-closed fallback. A structural test (`test_branch_prefix_allowlist.py`) asserts every prefix is covered by a `.github/workflows/python-verify.yml` push trigger, so a dropped prefix that would make a PR unmergeable fails CI. |
| `pr_strategy` | string | `"compact"` | PR-consolidation policy. `compact` ⇒ follow-up / config-migration / ad-hoc changes ride an already-pending related PR when the changed-file count stays within `pr_compact_max_changed_files`; `distinct` ⇒ always open a separate PR. The `manage-config project pr-decision --changed-files N` verb resolves this knob (with `pr_compact_max_changed_files`) into a `ride|split` decision — see `manage-config` Canonical invocations → `project pr-decision`; it is the consult surface every PR-opening guidance references rather than re-deriving the comparison. |
| `pr_compact_max_changed_files` | int | `150` | The compact-strategy ceiling: under `pr_strategy: compact`, a change riding an existing PR splits into its own PR once the changed-file count exceeds this value. Resolved together with `pr_strategy` by the `manage-config project pr-decision --changed-files N` consult verb (see `manage-config` Canonical invocations → `project pr-decision`). |
| `merge_queue_managed_externally` | bool | `false` | Declares that the repository's merge queue is owned by an org- or externally-managed ruleset rather than by plan-marshall. When `true`, `marshall-steward` never prompts to create or enable a queue and never reconciles a foreign ruleset — it only aligns the `use_merge_queue` step param to the detected platform state (see `marshall-steward/references/merge-queue-setup.md` § Step MQ-0). It also short-circuits the probe-backed set-time validation of `use_merge_queue`, since plan-marshall has neither the standing nor necessarily the token scope to adjudicate a foreign queue's eligibility. |

## Section: credentials_config

Non-secret per-provider configuration (committed, shared via git), written by `manage-providers credentials edit --extra` / `configure --extra`. Holds the non-secret extra fields a provider integration needs (e.g. SonarCloud `organization` / `project_key`); the secret token is stored separately in the out-of-tree credential file under `~/.plan-marshall/credentials/` (the machine-global home root, overridable via `PLAN_MARSHALL_HOME`), never here. The block is keyed by the fully-qualified `bundle:skill` provider name. It is absent until the first `--extra` upsert; `save_config` orders it canonically between `build` and `project` (see `CANONICAL_TOP_LEVEL_KEY_ORDER` in `_config_core.py`).

### Structure

```json
{
  "credentials_config": {
    "plan-marshall:workflow-integration-sonar": {
      "organization": "cuioss",
      "project_key": "cuioss_plan-marshall"
    }
  }
}
```

### Fields (per provider entry)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `<key>` | string | No | A non-secret provider-config field (e.g. `organization`, `project_key` for SonarCloud). Keys are provider-defined; `manage-providers` upserts them idempotently via `--extra KEY=VALUE`. |

## Section: skill_domains

Skill configuration per domain. See [skill-domains.md](skill-domains.md) for complete domain structure, profiles, validation rules, and technical domain catalog. See [skill-domains-operations.md](skill-domains-operations.md) for resolution commands and usage patterns.

Key structural summary:
- **System domain**: Contains `defaults` and `optionals`
- **Technical domains**: Reference a `bundle` and declare `workflow_skill_extensions` (outline, triage)
- **Profiles**: Loaded at runtime from `extension.py`, not stored in marshal.json
- **Domain inclusion (optional)**: A `skill_domains.{domain}` entry MAY carry two additive, operator-set inclusion keys — `always_on` (bool, default absent ⇒ `false`) and `file_globs` (list[str], default absent) — that union the domain into a plan's `references.domains` set unconditionally (`always_on`) or on a file-glob match against the plan's affected files (`file_globs`). Both are absent by default (no seed, so `sync-defaults` neither adds nor wipes them), validated by `validate_domain_inclusion`, and preserved across a `skill-domains configure` reconfigure. Set via `skill-domains set-inclusion`. See [skill-domains.md § Domain Inclusion](skill-domains.md).

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
    },
    "provisioned_version": "0.1.42",
    "config_seed_fingerprint": "a1b2c3…"
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

### Provisioning Fields

Runtime-stamped by `stamp_provisioning_fields()` (in `_config_defaults.py`) at both `init` and `sync-defaults` time — NOT part of `get_default_config()`. They record the marketplace version and default-config-seed fingerprint this `marshal.json` was last provisioned against, so the `generate_executor preflight` verb can signal executor/config staleness against the installed `dist-manifest.json`. Neither follows the key-exists preservation in `manage-config/SKILL.md` § "Workflow: Sync Defaults", but their override conditions differ: `config_seed_fingerprint` is re-stamped unconditionally on every `sync-defaults` run, while `provisioned_version` advances only when `read_provisioned_version()` returns a real (non-empty) version — an empty read (unstamped/absent executor) preserves any pre-existing `provisioned_version` instead of blanking it.

| Field | Type | Description |
|-------|------|-------------|
| `provisioned_version` | string | The `MARSHALL_VERSION` (`0.1.N`) the executor/config was provisioned at, from the installed `dist-manifest.json`. Compared against `dist-manifest.json`'s `config_changed_at_version` to advise a steward reconcile on config-seed drift. |
| `config_seed_fingerprint` | string | Canonical-JSON hash of `get_default_config()` at provisioning time (the same hash the target generator stamps as `config_seed_fingerprint` in `dist-manifest.json`). |

## Section: plan

Phase-specific configuration for the 6-phase workflow model. Each phase with configurable settings has its own sub-section.

> **Phase naming**: JSON keys use the `phase-{N}-{name}` prefix form (e.g., `phase-1-init`). The canonical phase name is `1-init` — see [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the standard phase list.

### Plan-level (non-phase) fields

These fields live directly under `plan`, outside any phase block.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `open_in_ide` | bool | true | Whether Plan Marshall attempts to open the plan/worktree in the IDE on creation. A missing key is also treated as `true` by `manage-files open-in-ide`. Set `false` to suppress IDE auto-open. |
| `finding_raw_input_max_bytes` | int | 65536 | Per-field byte cap for quarantined `raw_input.{field}` free-text in the findings ledger. Every producer files untrusted free-text (PR-comment body, Sonar message, …) under the `raw_input.{field}` quarantine sub-namespace; the ledger caps each field at this many bytes and appends a `[truncated]` marker on overflow. The 64 KiB default is corpus-grounded (p99 ≈ 21 KB, max ≈ 68 KB across 399 PR-comment findings), retaining the full body for effectively every real finding while bounding a hostile oversized payload. Callers thread the resolved value into `manage-findings ... --raw-input-max-bytes`. |

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
      "escalation": "auto",
      "lane_selection": "ask",
      "lane_prune_thresholds": {
        "confidence_complete": 95,
        "linear_change_max_deliverables": 1
      }
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `branch_strategy` | string | "feature" | direct, feature |
| `use_worktree` | bool | true | Whether the plan allocates an isolated worktree. `true` (default, with `branch_strategy: feature`) materialises a worktree at `.plan/local/worktrees/{plan-id}/` during `phase-5-execute` Step 2.5; `false` runs against the main checkout. |
| `init_without_asking` | bool | true | Auto-continue from `phase-1-init` to `phase-2-refine`. `true` (default) skips the gate; `false` stops after init and waits for the user. |
| `deep_lane` | enum(`auto`\|`always`\|`never`) | auto | `gate_mode` gate for the precondition-driven deep planning lane. Consumed by the phase-1-init `planning-lane route`. `always` forces deep; `never` forces light (the DQ3 hard-escalation ratchet still fires unless `escalation` is also `never`); `auto` defers to the DQ1 signal set. Validated by `validate_gate_mode` at set-time. |
| `escalation` | enum(`auto`\|`always`\|`never`) | auto | `gate_mode` gate for the hard-escalation safety ratchet (DQ3 explosion / build-break / premise). `auto` keeps it live; `never` is the explicit full-speed-full-risk opt-in. Validated by `validate_gate_mode` at set-time. |
| `lane_selection` | enum(`ask`\|`auto`) | ask | Whether init PROMPTS for the execution-profile posture (`ask` surfaces the minimal/auto/full dialogue) or silently takes the computed `auto` projection (`auto`). Validated by `validate_lane_selection`. The per-element lane vocabulary (closed `lane.class` enum, class→default tier table, prune-predicate names) is owned by [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md). |
| `lane_prune_thresholds` | dict | `{confidence_complete: 95, linear_change_max_deliverables: 1}` | Tunable numeric thresholds the `auto` posture evaluates its prunable-element predicates against at manifest-compose time. `confidence_complete` (int 0–100) is the post-init confidence floor that prunes `refine`; `linear_change_max_deliverables` (int ≥ 1) is the deliverable-count ceiling that prunes the 4-plan decomposition element. The boolean predicates (`no_code_delta`, `footprint_no_lesson_component`) carry no threshold. Validated by `validate_lane_prune_thresholds` (exact key set + range enforcement). |

**Per-element lane override** (`plan.<phase>.steps.<step>.lane`, value ∈ `off`\|`minimal`\|`auto`\|`full`\|`ask`, validated by `validate_lane_override`): pins any lane-participating element to a fixed posture cutoff via the same nested step-param channel finalize-step params use. `off` never runs an `adversarial`/`prunable` element (a real opt-out), but a weakening `off` on a `derived-state`/`core` floor element is **immune** — it is ignored at compose time, the element stays at its class-default tier, and an informational note records the neutralized override; `minimal` force-keeps it in every posture; `auto`/`full` pin its tier; `ask` always surfaces it individually in the init dialogue. Absent by default — the shipped per-element default lives in each element's frontmatter `lane:` block, and `marshal.json` carries only the project / meta overrides.

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
| `revalidation` | enum(`auto`\|`always`\|`never`) | auto | `gate_mode` gate for the premise / narrative-vs-code safety check (light lane + deep refine). `never` disables the safety check. Validated by `validate_gate_mode` at set-time. |

### phase-3-outline

```json
{
  "plan": {
    "phase-3-outline": {
      "plan_without_asking": false,
      "q_gate_validation": "once"
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `plan_without_asking` | bool | false | Auto-proceed from outline to task creation without user review |
| `q_gate_validation` | enum(`off`\|`once`\|`until_clean`) | once | Planning-time q-gate validation knob consumed by the deep-lane outline dispatch. `off` skips q-gate validation; `once` (default) runs a single validation pass without re-looping on findings; `until_clean` re-runs validation until it reports no blocking findings. Validated by `validate_q_gate_validation`. Replaces the retired planning-time `qgate` run-at-all gate. |

### phase-4-plan

```json
{
  "plan": {
    "phase-4-plan": {
      "execute_without_asking": true,
      "q_gate_validation": "once"
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `execute_without_asking` | bool | true | Auto-continue to execute phase after task creation |
| `q_gate_validation` | enum(`off`\|`once`\|`until_clean`) | once | Planning-time q-gate validation knob consumed by phase-4-plan over the emerging task plan. `off` skips q-gate validation; `once` (default) runs a single validation pass without re-looping on findings; `until_clean` re-runs validation until it reports no blocking findings. Validated by `validate_q_gate_validation`. |

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
        "XS": "5K",
        "S": "25K",
        "M": "60K",
        "L": "130K",
        "XL": "260K",
        "XXL": "520K"
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
| `commit_and_push` | bool | true | true=commit per-deliverable + push at finalize; false=local-only run (push/PR steps stripped by the manifest `commit_push_disabled` pre-filter) |
| `max_iterations` | int | 5 | Maximum verify-execute-verify loops |
| `per_deliverable_build` | list[string] | `["default:verify:compile","default:verify:module-tests"]` | A list of `default:verify:{canonical}` step IDs — the canonical-verify rungs phase-5-execute runs for the changed module at each per-deliverable chain-tail point (Step 10). The default runs `compile` + the module's scoped `module-tests`. Set to `[]` to disable the focused build (the whole-tree sweep at end-of-phase remains the only build). Each entry must be a `default:verify:{canonical}` ID; the retired enum strings (`off` / `compile-only` / `compile+scoped-test` / `full`) are rejected with a migration error. |
| `cost_size_token_table` | dict | `{"XS":"5K","S":"25K","M":"60K","L":"130K","XL":"260K","XXL":"520K"}` | Size→token table mapping each T-shirt `cost_size` (`XS`/`S`/`M`/`L`/`XL`/`XXL`) to a predicted-token magnitude. The phase-4-plan bin-packer (`manage-tasks pack-envelopes`) reads it to map a task's derived `cost_size` to its `predicted_cost_tokens`. Keys must be exactly `XS`/`S`/`M`/`L`/`XL`/`XXL`; each value parses via `sensible_number.parse_sensible_int`. Validated by `validate_cost_size_token_table`. The four original magnitudes (`S`≈25K / `M`≈60K / `L`≈130K / `XL`≈260K) are calibrated to the forensic 134K–392K per-dispatch range; `XS`≈5K labels deterministic ≈0-token bookkeeping and `XXL`≈520K the heaviest elements. The magnitudes are tunable to recalibrate the cost model. |
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

```text
plan phase-5-execute remove-field --field steps
```

### phase-6-finalize

Finalize pipeline with a `steps` keyed map. `steps` serializes on disk as a JSON object keyed by step id: a config-less step maps to `{}`; a param-owning step maps to its nested param object. Step-owned params (`review_bot_buffer_seconds` under `plan-marshall:automatic-review`; `touched_file_cleanup` / `do_transition` / `ce_wait_timeout_seconds` under `default:sonar-roundtrip`; `pr_merge_strategy` / `final_merge_without_asking` / `auto_rebase_threshold` under `default:branch-cleanup`; `drop_review_on_scope_gate` under `default:pre-submission-self-review`) nest inside their owning step's value. Key insertion order is the execution order. The reader consumes the keyed map directly; it is the sole on-disk shape both read and written.

**All finalize steps are materialised** — the default config seeds EVERY discovered finalize-step implementor into the `steps` map; a step's exclusion is expressed as a `lane: off` override (in its param object), never as absence. A `default_on: false` step therefore appears in the seed carrying `lane: off`.

**`sync-defaults` materialises an explicit `lane` on every finalize step.** After the deep-merge, `manage-config sync-defaults` fills a `lane` value into every `plan.phase-6-finalize.steps` entry that carries none, by provenance: a **pre-existing** lane-less step is filled with its **frontmatter-class effective lane** — the value the composer would apply with no override (declared `lane.tier` ▸ class default: `core` / `derived-state` → `minimal`, `adversarial` / `prunable` → `auto`), a semantic no-op that surfaces the implicit default as an explicit value; a **freshly-merged default** step (one the config did not previously carry) is filled with `lane: off`, honoring the infra-steps-must-be-opt-in principle. A step already carrying an explicit `lane` (`off` / `ask` / a resolved tier) is left untouched, so the pass is idempotent. Because a weakening `off` on a `core` / `derived-state` floor element is **immune** at compose time (ignored, the element stays at its class-default tier), materialising the finalize set to a fully-explicit shape can never silently drop a correctness-floor step — a hand-written `off` on such a step is inert.

**The four finalize ceremony gates ride the `lane` channel, not a run-at-all knob.** `qgate` / `self_review` / `simplify` / `security_audit` are each governed by their owning step's per-element `steps.<step>.lane` override (`off`/`minimal`/`auto`) — resolved by the manifest ceremony transform (`off→never`, `minimal→always`, `auto`/absent`→auto`). There is no flat `qgate` sibling and no `simplify` / `self_review` run-at-all param. The owning steps are `pre-push-quality-gate` (qgate), `default:pre-submission-self-review` (self_review), `default:finalize-step-simplify` (simplify), and `default:finalize-step-security-audit` (security_audit). The `default:pre-submission-self-review` step retains only its `drop_review_on_scope_gate` escape hatch (default `false`, seeded under the step).

**The two adversarial infra elements seed `lane: ask`.** `plan-marshall:automatic-review` and `default:sonar-roundtrip` seed a `lane: ask` override so `marshall-steward` always prompts about them at setup / update-config and persists a resolved `off`/`auto`/`full`; a genuinely-unresolved `ask` whose provider is absent is dropped at compose time by the drop-when-no-provider safety net.

```json
{
  "plan": {
    "phase-6-finalize": {
      "max_iterations": 3,
      "checks_wait_timeout_seconds": 600,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "steps": {
        "default:pre-submission-self-review": {
          "drop_review_on_scope_gate": false
        },
        "default:finalize-step-simplify": {},
        "default:push": {},
        "default:create-pr": {},
        "plan-marshall:automatic-review": {
          "review_bot_buffer_seconds": 180,
          "lane": "ask"
        },
        "default:sonar-roundtrip": {
          "touched_file_cleanup": "new_code_only",
          "do_transition": false,
          "ce_wait_timeout_seconds": 600,
          "lane": "ask"
        },
        "default:lessons-capture": {},
        "default:branch-cleanup": {
          "pr_merge_strategy": "squash",
          "final_merge_without_asking": false,
          "auto_rebase_threshold": "no_overlap_only"
        },
        "default:record-metrics": {},
        "default:archive-plan": {}
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
| — (pre-push-quality-gate activation) | derived | — | The `default:pre-push-quality-gate` finalize step's activation is **derived from `build.map`** — no dedicated config key. The manifest composer activates the step when the live footprint touches any `glob` registered in `build.map`; an absent build_map or no footprint match leaves the step inactive. Its ceremony gate (`qgate`) rides `steps['pre-push-quality-gate'].lane` (`off`/`minimal`/`auto`), not a flat run-at-all knob. |
| `steps` | dict | (see below) | Keyed map of step references to execute (key insertion order = execution order), persisted sorted ascending by each step's authoritative `order` value. Config-less steps map to `{}`; param-owning steps map to their nested param object. The keyed map is both the internal normalized representation and the on-disk serial form. |

**Step-owned params (nested under their owning step in the `steps` map):**

`plan-marshall:automatic-review`:

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
| `ce_wait_timeout_seconds` | int | 600 | Budget (seconds) for the synchronous in-Python CE-readiness wait performed by `sonar.py fetch_findings` before enumerating new-code issues — the direct sibling of the flat `checks_wait_timeout_seconds`. An explicit `--ce-wait-timeout` flag overrides it. |

`default:branch-cleanup`:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `pr_merge_strategy` | string | "squash" | squash, merge, rebase — the merge method the branch-cleanup step passes to `pr merge`. |
| `final_merge_without_asking` | bool | false | Whether to merge the PR after CI passes without prompting the operator. `true` merges under the unified `manage-locks:merge_lock` cross-plan mutex (acquired by the branch-cleanup Pre-Merge Gate); `false` (default) prompts the operator before merging. |
| `auto_rebase_threshold` | string | "no_overlap_only" | Gates the pre-merge auto-rebase decision in `branch-cleanup.md`, orthogonal to `final_merge_without_asking`. `no_overlap_only` permits the auto-rebase only when it would touch a disjoint file set; any overlap defers to the operator. |

`default:finalize-step-simplify` is config-less — its `simplify` ceremony gate rides the step's `lane` override (`off`/`minimal`/`auto`), not a run-at-all param.

`default:pre-submission-self-review` (the on-by-default pre-submission self-review step) — the `self_review` ceremony gate rides the step's `lane` override, so only the `drop_review_on_scope_gate` escape hatch remains as a step-owned param:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `drop_review_on_scope_gate` | bool | false | Escape hatch for the manifest composer's `scope_gated_finalize` pre-filter. `false` (default) keeps the bot-review invariant intact; `true` opts into additionally dropping `plan-marshall:automatic-review` on scope-gated (surgical / single_module) plans. The self-review step owns this knob because it is the primary review step the scope gate suppresses. |

**Two-tier source for step params**: the `steps` keyed map in `marshal.json` is the **compose-time default + wizard global-config write target** (read/written via `step get` / `step set`). The **plan-local runtime source** is the execution manifest — the composer snapshots each selected step's resolved params into the manifest body at compose time, and phase-5/6 runtime consumers read params via `manage-execution-manifest step-params get` (plan-local, per-plan overridable via `step-params set`), NOT from `marshal.json`. The execution manifest's `step_params` block is an id-keyed dict — a separate runtime-override surface. See [manage-execution-manifest/standards/manifest-schema.md](../../manage-execution-manifest/standards/manifest-schema.md) § `step_params`.

Managed via (the step verbs operate on the keyed map, preserving key insertion order and existing per-step params):
- `plan phase-6-finalize set-steps --steps default:push,default:create-pr,…`
- `plan phase-6-finalize add-step --step my-bundle:my-finalize-step`
- `plan phase-6-finalize remove-step --step default:sonar-roundtrip`
- `plan phase-6-finalize step get --step-id default:branch-cleanup` (returns the step's complete nested param object in one call)
- `plan phase-6-finalize step set --step-id default:branch-cleanup --param pr_merge_strategy --value rebase` (writes one step-owned param into the step's nested object — the global-config write target)

Default steps (execution order): `default:pre-submission-self-review`, `default:finalize-step-simplify`, `default:push`, `default:create-pr`, `plan-marshall:automatic-review`, `default:sonar-roundtrip`, `default:lessons-capture`, `default:branch-cleanup`, `default:record-metrics`, `default:archive-plan`. Step types: built-in (`default:` prefix), project (`project:` prefix), skill (fully-qualified `bundle:skill`).

### gate_mode planning gates and finalize automation knobs (phase-local)

The three surviving lifecycle gates ride the `gate_mode` enum (`auto|always|never`, validated at set-time by `validate_gate_mode`), each a flat phase-local knob owned by the phase whose decision machinery consumes it: `deep_lane` / `escalation` under `phase-1-init`, `revalidation` under `phase-2-refine`. There is no top-level policy block. `deep_lane` / `escalation` are consumed by the phase-1-init lane router, and `revalidation` by the refine revalidation pass. (The planning-time Q-Gate dispatch on `phase-3-outline` / `phase-4-plan` is governed by the distinct `q_gate_validation` knob — `off`/`once`/`until_clean` — not a `gate_mode` gate; see those phase sections above.)

The four **finalize ceremony gates** — `qgate`, `self_review`, `simplify`, `security_audit` — no longer ride a run-at-all knob. Each is governed by its owning step's per-element `steps.<step>.lane` override (`off`/`minimal`/`auto`), consumed by the manifest composer's finalize-selection ceremony transform (`off→never`, `minimal→always`, `auto`/absent`→auto`) — see [`manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md) § "plan.phase-6-finalize Selection". Under `phase-6-finalize` the flat phase-level knobs are the two automation knobs (`finalize_without_asking` / `loop_back_without_asking`, boolean) and the timeout/iteration knobs; every ceremony gate rides its owning step's `lane` override, and `drop_review_on_scope_gate` / `final_merge_without_asking` remain step-owned params (see the per-step param sub-tables above).

**Access shape.** Read/write the `gate_mode` planning gates and the flat automation knobs via the standard `manage-config plan <phase> get/set --field <knob>` verb; read/write the finalize ceremony gates by setting the owning step's `lane` override (`step set --step-id <owning-step> --param lane --value <off|minimal|auto>`) and the other step-owned knobs (`drop_review_on_scope_gate`, `final_merge_without_asking`) via the same `step get/set --step-id <owning-step>` verb. See [`manage-config/SKILL.md`](../SKILL.md) § "Phase-Local gate_mode Gates and Automation Knobs".

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

**Coupling constraint** — `reject thoroughness ≥ T4 ∧ scope < component`. A relation-tracing thoroughness (T4/T5) cannot be honoured below `component` scope because the siblings the relations point at are out of radius. The constraint is enforced at lookup time (from both `coverage read` and `coverage resolve`) with `error_type: coverage_coupling_violation`. An `inherit` on either field is unconstrained. The constraint is defined verbatim in [`persona-plan-marshall-agent/standards/thoroughness.md`](../../persona-plan-marshall-agent/standards/thoroughness.md) § Coupling Constraint.

`plan.coverage` is the project-default knob (seeded `inherit/inherit`); the `read`/`resolve` verbs read `marshal.json` only (no per-plan tier). The per-invocation user-gathered identifier + expanded instruction live in `status.json` metadata per the [coverage-gathering contract](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md) — the components that implement that contract are coverage's consumers. `coverage resolve` is the project-default tier those components fall back to when no per-invocation cell was gathered.

Resolved via:
- `coverage read --phase phase-5-execute` (resolve a phase's cell, project default)
- `coverage resolve --phase phase-5-execute` (resolve cell + coupling result, project default)
- `coverage read --default` (raw `plan.coverage` lookup)
- `coverage expand --thoroughness T3 --scope component` (static identifier → contract instruction block; `inherit/inherit` → behavior-preserving instruction)

## CI Provider Resolution

There is no top-level `ci` block. The CI provider is resolved from the `providers[]` array (the entry whose `category == 'ci'`, mapping `plan-marshall:workflow-integration-github` → `github` and `plan-marshall:workflow-integration-gitlab` → `gitlab`). The CI-completion polling timeout lives under `plan.phase-6-finalize.checks_wait_timeout_seconds` (a finalize wait-policy — see § `phase-6-finalize`). Tool availability is verified live via `plan-marshall:tools-integration-ci:ci_health verify-all` — it is not persisted, since tool/auth status varies per developer machine and is cheap to check on demand.

## Default Values

Default values are defined in:

```text
plan-marshall/skills/manage-config/scripts/_config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
