---
name: manage-config
description: Project-level infrastructure configuration for marshal.json
user-invocable: false
mode: script-executor
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
- Every addition, removal, relocation, or rename of a config field MUST satisfy the governance rules in [standards/config-design-principles.md](standards/config-design-principles.md) — ownership boundaries (Rule 1 foreign-system, Rule 2 meta-project convention), placement (Rule 5), anti-speculation (Rule 6), and the lossless field-migration mechanics (Rule 3).

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
  `final_merge_without_asking: true` (nested under `steps['default:branch-cleanup']`)
  survives even when the default is `false`.
- **Exception — provisioning stamps**: `system.provisioned_version` and
  `system.config_seed_fingerprint` are the two runtime-stamped provisioning fields
  (written by `stamp_provisioning_fields()` at both `init` and `sync-defaults` time,
  NOT part of `get_default_config()`). Unlike every other already-present key, these
  two are re-stamped **unconditionally** on each `sync-defaults` run — the
  key-exists preservation above does not apply to them — so a live `marshal.json`
  always reflects the currently provisioned version and config-seed fingerprint
  after a steward reconcile. See `marshall-steward/SKILL.md` config-reconcile step.
- Nested dicts are merged recursively, so a deeply-nested missing sub-key
  (e.g. the `auto_rebase_threshold` param under
  `plan.phase-6-finalize.steps['default:branch-cleanup']` when that step's param
  object exists but the param does not) is added without disturbing siblings.
- Lists are atomic: a present list is kept verbatim; only an absent list key is
  seeded from defaults.
- The merge is idempotent — re-running immediately produces an empty `added[]`.

**Output** (TOON):

```toon
status: success
added[3]:
  - plan.phase-5-execute.per_envelope_budget_tokens
  - plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold
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
  plan phase-5-execute set --field commit_and_push --value false

# Select the per-deliverable build — comma-separated list of default:verify:{canonical} step IDs (empty disables it)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field per_deliverable_build --value default:verify:compile,default:verify:module-tests

# Tune the per-envelope packing budget consumed at plan time by the bin-packer
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field per_envelope_budget_tokens --value 400K
```

**phase-5-execute build + cost-sizing fields:**

| Field | Type | Default | Semantics |
|-------|------|---------|-----------|
| `per_deliverable_build` | list[`default:verify:{canonical}`] | `[default:verify:compile, default:verify:module-tests]` | Canonical-verify rungs phase-5-execute runs at each per-deliverable chain-tail point (Step 10), module-scoped to the changed module. The default runs compile + scoped `module-tests`; `[]` disables the per-deliverable build (the end-of-phase sweep is the only build). The retired enum strings (`off` / `compile-only` / `compile+scoped-test` / `full`) are rejected with a migration error. Read by phase-5-execute per-deliverable. |
| `cost_size_token_table` | dict[`XS`/`S`/`M`/`L`/`XL`/`XXL` → magnitude] | `{XS: 5K, S: 25K, M: 60K, L: 130K, XL: 260K, XXL: 520K}` | Size→token table mapping each T-shirt `cost_size` to a predicted-token magnitude. The phase-4-plan bin-packer (`manage-tasks pack-envelopes`) reads it to map a task's derived `cost_size` to its `predicted_cost_tokens`. Keys must be exactly `XS`/`S`/`M`/`L`/`XL`/`XXL`; each value parses via `sensible_number.parse_sensible_int`. Tune the magnitudes to recalibrate the cost model from observed post-return `<usage>`. Read via `manage-config plan phase-5-execute get --field cost_size_token_table`. |
| `per_envelope_budget_tokens` | string (sensible int) | `"400K"` | Per-envelope packing budget — the token ceiling the phase-4-plan bin-packer accumulates `predicted_cost_tokens` against before opening a new envelope group. Consumed at PLAN time by the bin-packer, NOT a runtime comparand. The `_tokens` suffix names the unit; the value parses via `sensible_number.parse_sensible_int`. Read via `manage-config plan phase-5-execute get --field per_envelope_budget_tokens`. |

**Symmetric auto-continuation knobs:** the forward (`finalize_without_asking`) and reverse (`loop_back_without_asking`) auto-continuation knobs are flat knobs under `plan.phase-6-finalize` — read/written via the standard `manage-config plan phase-6-finalize get/set --field <knob>` access shape. (`final_merge_without_asking` is a step-owned param of `default:branch-cleanup`, read/written via the one-stop `step get`/`step set` verb — not a flat field.)

### Manage Verification Steps

> **Step-map fields reject `set --field`.** The phase's keyed step-map field — `verification_steps` for `phase-5-execute` and `steps` for `phase-6-finalize` — serializes on disk as the keyed-map serial form (a JSON object keyed by step id), NOT a scalar. The scalar `set --field` verb rejects these two fields with a structured error (`Field '{field}' is a keyed step-map and cannot be set via 'set --field'. Use: set-steps, add-step, remove-step, or step set.`) and mutates nothing. Use the step verbs below (`set-steps` / `add-step` / `remove-step`) to manage the step map, and `step get`/`step set` to read or write a step's nested params. The reader consumes the keyed map directly — it is the sole on-disk shape both read and written. Only genuine scalar fields (e.g. `commit_and_push`, `max_iterations`, `finalize_without_asking`) are settable via `set --field`.

`set-steps` and `add-step` resolve each step's `order` from its authoritative source (frontmatter on built-in standards docs, or frontmatter on project-local `SKILL.md` for `project:` steps) and persist the steps list sorted ascending by that value. They return `error: missing_order` or `error: order_collision` when a step has no declared order or two steps share the same value — fix the offending step's authoritative source.

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

### Coverage two-knob configuration

Coverage is a two-dial contract — `thoroughness` (T1–T5) × `scope` (change-set…overall) — orthogonal to the `effort` model-tier dial. A per-phase override lives under the phase entry's `coverage` key; the plan-wide fallback is `plan.coverage` (seeded `inherit/inherit`). The `read`/`resolve` verbs mirror the `effort` resolver's lookup shape, resolving each field independently from `marshal.json` only (the project-DEFAULT tier — no per-plan tier), and enforcing the scope↔thoroughness coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) at lookup time. See [`persona-plan-marshall-agent/standards/thoroughness.md`](../persona-plan-marshall-agent/standards/thoroughness.md) § Coupling Constraint.

`coverage`'s consumers are the broad-pass components that implement the [coverage-gathering contract](../persona-plan-marshall-agent/standards/coverage-gathering-contract.md) — wide audits, compliance sweeps, simplification/refactor campaigns, pre-submission review. Each gathers a `(thoroughness, scope)` cell from the user at invocation, expands it via `coverage expand`, persists the identifier + expanded instruction in `status.json` metadata, and consumes the expanded instruction to govern its breadth/depth. `coverage resolve` is the project-default tier consulted when no per-invocation cell was gathered.

```bash
# Resolve the coverage cell for a phase (project default)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  coverage read --phase phase-5-execute

# Resolve cell + coupling result (project default)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  coverage resolve --phase phase-5-execute

# Raw plan-wide fallback
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  coverage read --default

# Expand the identifier into the contract's operational instruction block
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  coverage expand --thoroughness T3 --scope component
```

`coverage expand` is the static identifier→instruction expander (backed by `coverage_presets.py`): it maps the `(thoroughness, scope)` identifier to the canonical operational instruction text defined by the coverage-gathering contract's expansion table. `inherit/inherit` expands to the behavior-preserving instruction. An incoherent cell (e.g. `thoroughness: T4`, `scope: change-set`) is rejected at lookup/expand time with `error_type: coverage_coupling_violation`; unconfigured fields resolve to `inherit`.

### Resolve Skills for a Domain and Profile

```bash
# Get aggregated skills for java implementation profile
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain java --profile implementation
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

## Workflow: Phase-Local Run-at-all Gates and Automation Knobs

**Pattern**: Read-Process

The lifecycle run-at-all gates and automation knobs are flat knobs under their owning phase — read/written through the standard `plan <phase> get/set --field <knob>` verb. Each gate takes `auto|always|never` (validated by `validate_run_at_all`); the automation knobs are boolean. Distribution:

| Knob | Location | Read via |
|------|----------|----------|
| `deep_lane` | `plan.phase-1-init` | `plan phase-1-init get --field deep_lane` |
| `escalation` | `plan.phase-1-init` | `plan phase-1-init get --field escalation` |
| `auto_route_recipe` | `plan.phase-1-init` | `plan phase-1-init get --field auto_route_recipe` |
| `auto_route_recipe_threshold` | `plan.phase-1-init` | `plan phase-1-init get --field auto_route_recipe_threshold` |
| `revalidation` | `plan.phase-2-refine` | `plan phase-2-refine get --field revalidation` |
| `finalize_without_asking` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field finalize_without_asking` |
| `loop_back_without_asking` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field loop_back_without_asking` |
| `final_merge_without_asking` | `plan.phase-6-finalize.steps['default:branch-cleanup']` (step-owned param) | `plan phase-6-finalize step get --step-id default:branch-cleanup` (read `final_merge_without_asking` off `params`) |
| `self_review` | `plan.phase-6-finalize.steps['project:finalize-step-pre-submission-self-review']` (step-owned param) | `plan phase-6-finalize step get --step-id project:finalize-step-pre-submission-self-review` (read `self_review` off `params`) |
| `qgate` (finalize) | `plan.phase-6-finalize` | `plan phase-6-finalize get --field qgate` |
| `simplify` | `plan.phase-6-finalize.steps['default:finalize-step-simplify']` (step-owned param) | `plan phase-6-finalize step get --step-id default:finalize-step-simplify` (read `simplify` off `params`) |
| `drop_review_on_scope_gate` | `plan.phase-6-finalize.steps['project:finalize-step-pre-submission-self-review']` (step-owned param) | `plan phase-6-finalize step get --step-id project:finalize-step-pre-submission-self-review` (read `drop_review_on_scope_gate` off `params`) |

### Read an automation knob

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field finalize_without_asking
```

**Output** (TOON):

```toon
status: success
phase: phase-6-finalize
field: finalize_without_asking
value: true
```

### Read a run-at-all gate

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field qgate
```

The `get` verb is read-only — it never mutates `marshal.json`. An unresolvable field returns `error_type: field_not_found`.

---

## Workflow: Build Map

**Pattern**: Script Automation

The `build.map` block in `marshal.json` is the file-to-build contract: a domain-keyed inventory of `{glob, role, build_class}` entries that maps every changed path to the build action it requires. It lives at the top-level `build.map` block (its owning block, peer to `build.queue`) and is populated from the registered domain extensions with write-once semantics — an existing seed survives a re-seed so user corrections are preserved. The seeded globs are **explicit `(pattern, role)` routes**: each extension declares its routes directly via `classify_globs()` (single-`*` fnmatch globs for path-bearing routes, never recursive `**`; a bare config-file basename route like `pom.xml` or `package.json` matches the file at any tree depth, not only a root-level instance), and the `script-shared` route collector gathers them verbatim. A separate git-tracked completeness validator scans `git ls-files` and flags any tracked source file no declared route covers, so a forgotten production module surfaces rather than silently classifying to no build. There is no separate override layer; corrections are made directly to the seeded entries.

**Applicability scoping.** The seed includes a domain's routes only when that domain applies to the project. `aggregate_build_map()` consults each domain's owning extension's `applies_to_module()` against the discovered project modules and keeps the domain's routes only when `applies_to_module()` reports `applicable: True` for at least one discovered module — the same applicability predicate architecture enrichment uses. A Python-only project therefore never receives `java` / `oci` / `javascript` routes merely because those bundles are installed. Because applicability is resolved against discovered modules, the seed is **post-architecture-only**: when module discovery yields no modules (architecture not yet discovered) the aggregation is empty.

**Seed point.** The build map is **not** populated at `init` or by `sync-defaults` — `get_default_config()` does not include a `build_map` block, so neither the `init` write nor the `sync-defaults` deep-merge seeds it. The wizard's Step 8b (`build-map seed`, run after architecture discovery) is the **sole authoritative seed point**; the write-once guard makes that first explicit seed authoritative. Re-run `build-map seed` whenever a domain extension is added or updated.

**Drift detection.** Because the seed is write-once, a persisted `build.map` can grow stale relative to the live-tree derivation as extensions add or change `classify_globs()` routes. The read-only `build-map drift` verb surfaces that staleness: it diffs the persisted block against the current derivation and returns `in_sync` plus per-domain `added_globs` / `removed_globs`, never mutating `marshal.json`. The steward consumes this verb at menu-mode entry to gate an interactive re-seed (Y/N → `build-map seed --force` on yes / leave untouched on no), so the `--force` path is no longer the only way a stale map gets surfaced — see [`marshall-steward/SKILL.md`](../marshall-steward/SKILL.md) § "Re-Run Remediation Pass".

### Seed the Build Map

Re-seeds `build.map` from every *applicable* registered extension's `classify_globs()` + `classify_build_class()` predicates. The aggregator collects each applicable extension's explicit `(pattern, role)` routes verbatim; `classify_build_class()` then stamps each route with its canonical-named `build_class` (the `build_class` value IS the canonical command — there is no indirection map). Write-once: an existing `build_map` block is never clobbered — only a missing block is populated. Run `build-map seed` at wizard Step 8b (after architecture discovery) and again whenever a domain extension is added or updated.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed
```

**Output** (TOON):

```toon
status: success
action: seeded
domain_count: 1
build_map:
  python: [...]
```

`action` is `seeded` when a missing block was written, or `preserved` when an existing block was left untouched (write-once). `domain_count` is the number of applicable domains in the resulting block.

#### Force a clean re-derivation

`build-map seed --force` bypasses the write-once guard: it clears any existing `build_map` and re-derives a clean one from the current project state (current extensions, current applicability against the discovered modules). Use it to discard stale or hand-edited entries — for example after an extension's `classify_globs()` routes change, since a plain re-seed preserves the existing block and would not pick up the new routes.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed --force
```

When `--force` clears and rewrites an existing block, `action` is `re-derived` (versus `seeded` for a first-time write into a missing block).

#### Detect drift against the live derivation

`build-map drift` is a **read-only** diff: it derives the current map from the applicable extensions (the same derivation `seed` uses) and compares it against the persisted `build.map`, returning `in_sync` plus the per-domain added/removed-glob diff. It never mutates `marshal.json`. The steward's menu-mode entry consumes this verb to gate an interactive re-seed without clobbering deliberate hand-edits.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map drift
```

**Output** (TOON):

```toon
status: success
in_sync: false
drift:
  python:
    added_globs: [...]
    removed_globs: [...]
```

`in_sync` is `true` when the persisted map matches the derivation (the `drift` block is empty); `false` when any domain has `added_globs` (present in the derivation, absent from the persisted block) or `removed_globs` (the reverse).

### Read the Effective Build Map

Returns the effective build map read from `build.map`. This is the map the `architecture derive-verification` command reads to emit a task's verification command set. The read **fails closed**: when `build.map` is absent it returns a structured error rather than an empty map.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map read
```

**Output** (TOON):

```toon
status: success
build_map:
  python: [...]
domain_count: 1
```

`domain_count` is the number of domain keys in the returned `build_map`.

> **Schema and semantics**: See [standards/data-model.md § build_map](standards/data-model.md) for the `{glob, role, build_class}` entry schema, the tree-derived seed contract, and the closed canonical-named `build_class` set.

### Decide Whether a Build Must Run

`build-decision` is the centralized build-necessity decision API. It returns a structured `build` / `not_necessary` verdict for a canonical command (e.g. `quality-gate` / `verify` / `coverage`) against a plan's live footprint, so the consumer sites no longer each re-derive the decision inline. The verdict is a pure function of the `build.map` globs and the live plan footprint — no LLM judgement:

- `decision: build` when the footprint touches at least one registered build_map glob.
- `decision: not_necessary` (always carrying a non-empty, log-friendly `reason`) when the build_map registers no globs, the footprint is empty, or the footprint intersects no build glob.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-decision \
  --command quality-gate --plan-id my-plan
```

**Output — `build` verdict** (TOON):

```toon
status: success
decision: build
canonical_command: quality-gate
```

**Output — `not_necessary` verdict** (TOON):

```toon
status: success
decision: not_necessary
reason: plan footprint touches no build_map glob — only non-buildable files changed
canonical_command: quality-gate
```

The decision logic itself lives in the build-system-owned `should_execute_build` helper in `script-shared`; `build-decision` is a thin wrapper exposing it through the `manage-config` command surface (the home that already owns the `build_map` seed and footprint-matching logic the decision reuses).

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
| `ext-defaults` | get, set, set-default, list, remove |
| `system` | retention get, retention set |
| `project` | `get/set` (`default_base_branch`, `working_prefixes`) |
| `plan` | `{phase} get/set` (incl. run-at-all gates + flat finalize automation knobs), `{phase} step get/set` (one-stop keyed-map step-param read/write), set-steps, add-step, remove-step, set-max-iterations |
| `effort` | `read` (role/phase/`--default` resolver), `resolve-target` (`execution-context-{level}` variant name), `apply-preset --preset` (whole-tree writer), `set --scope {phase}.{role}\|plan --level` (surgical per-scope writer) |
| `ci` | get, get-provider, get-tools, get-command, set-provider, set-tools, persist |
| `build-map` | `seed` (re-seed `build.map` from applicable extensions, write-once; `--force` clears + re-derives), `read` (effective map from `build.map`, fail-closed when absent), `drift` (read-only diff of persisted vs derived map: `in_sync` + per-domain added/removed globs) |
| `build-decision` | `--command --plan-id` (centralized build-necessity verdict: `build` / `not_necessary`; `not_necessary` carries a log-friendly `reason`) |
| `init` | Initialize marshal.json (with optional `--force`) |
| `normalize-keys` | Re-write `marshal.json` with the canonical top-level key order (silent, idempotent; reuses the `save_config` key-order writer) |
| `domain-detect` | `--plan-id [--domain-override]` (deterministic detector for phase-1-init Step 7; walks `request.md` clarified narrative for explicit mentions of configured `skill_domains` and their bundle aliases; returns `domain` + `ambiguous` boolean. Single-domain projects auto-select; multi-match or zero-match returns `ambiguous=true` so the caller raises `AskUserQuestion` — no LLM dispatch fallback applies.) |
| `recipe-match` | `--request-text [--threshold 0.6]` (Tier 1 recipe-match for phase-1-init; scores free-form request text against the live recipe registry via the shared `recipe_scoring` core; returns ranked `matches[]` + `top_match` + `meets_auto_route_threshold`. Heuristic-first, zero LLM call inside the script — the bounded LLM fallback is orchestrator-driven.) |
| `aspect-classify` | `--request-text [--threshold 0.7]` (request-aspect classifier for phase-1-init; scores free-form request text against fixed analysis/planning/implementation keyword tables via `recipe_scoring.tokenize`; returns `aspect` + `confidence` + `drops_build_steps` + per-aspect `breakdown`. A winning analysis/planning aspect is accepted only when its `_overlap_score` confidence clears `>= --threshold` (default `0.7`, NO `0.6` cap) AND beats the implementation overlap; below threshold the safe `implementation` fallback keeps build/quality-gate/test gates. Heuristic-first, zero LLM call inside the script — the bounded LLM fallback is orchestrator-driven.) |

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
      "temp_on_maintenance": true
    }
  },
  "build": {
    "queue": {
      "max_slots": 5,
      "max_retries": 10
    }
  },
  "plan": {
    "phase-1-init": {
      "branch_strategy": "feature",
      "deep_lane": "auto",
      "escalation": "auto",
      "auto_route_recipe": true,
      "auto_route_recipe_threshold": 0.6,
      "lane_selection": "ask",
      "lane_prune_thresholds": {
        "confidence_complete": 95,
        "linear_change_max_deliverables": 1
      }
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "revalidation": "auto"
    },
    "phase-3-outline": {
      "plan_without_asking": false,
      "q_gate_validation": "once"
    },
    "phase-5-execute": {
      "commit_and_push": true,
      "max_iterations": 5,
      "per_deliverable_build": ["default:verify:compile", "default:verify:module-tests"],
      "verification_steps": {
        "default:verify:quality-gate": {},
        "default:verify:module-tests": {},
        "default:verify:coverage": {}
      }
    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "qgate": "auto",
      "steps": {
        "default:push": {},
        "default:create-pr": {},
        "plan-marshall:automatic-review": { "review_bot_buffer_seconds": 180 },
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
        "default:archive-plan": {}
      }
    }
  }
}
```

### Phase-Local Run-at-all Gates and Automation Knobs

The lifecycle run-at-all gates and finalize automation knobs are flat phase-local knobs, each owned by the phase whose decision machinery consumes it. Every gate takes `auto|always|never` (validated by `validate_run_at_all`): `auto` defers to the existing machinery (lane router / manifest composer), `always` forces the gate in, `never` skips it. The automation knobs are boolean.

**Run-at-all gates:**

| Gate | Owning phase | Controls |
|------|--------------|----------|
| `deep_lane` | `phase-1-init` | Whether the precondition-driven deep planning lane runs (phase-1-init lane router). `never` forces light, but a hard escalation still ratchets unless `escalation: never` is also set. |
| `escalation` | `phase-1-init` | Whether the hard-escalation safety ratchet (explosion / build-break / premise) stays live. `auto` keeps it live; `never` is the explicit full-speed-full-risk opt-in. |
| `revalidation` | `phase-2-refine` | Whether the premise / narrative-vs-code safety check runs (light lane + deep refine). |
| `self_review` | `phase-6-finalize` | Whether the pre-submission structural + cognitive self-review runs (manifest finalize step-selection). |
| `qgate` | `phase-6-finalize` | Whether finalize re-captures blocking findings. **Highest-risk gate** — `never` can mask real build/test failures. |
| `simplify` | `phase-6-finalize` | Whether the holistic post-implementation simplification sweep (`finalize-step-simplify`) runs. `always` forces it in even when the composer's `simplify_inactive` pre-filter would drop it; `never` skips it; `auto` defers to that pre-filter. |

**Flat phase-1-init recipe-match knobs (under `phase-1-init`):**

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `auto_route_recipe` | bool | `true` | Whether a high-confidence Tier 1 recipe match (top confidence `>= auto_route_recipe_threshold`) auto-routes to the matched recipe without prompting. `false` proposes the ranked matches via `AskUserQuestion` first. |
| `auto_route_recipe_threshold` | float | `0.6` | Auto-route confidence threshold for the Tier 1 recipe match. Default `0.6` because free-form requests carry no plan domain/scope, so keyword-overlap-only confidence caps at `0.6` — the same threshold the `recipe-match` verb's `--threshold` default uses. The `aspect-classify` verb is unrelated: it scores via `_overlap_score` (request-token / keyword-table overlap fraction, 0.0–1.0) with NO `0.6` cap, so it carries its own `0.7` default threshold — do not conflate the two. |

**Execution-profile lane knobs (under `phase-1-init`):**

The lane mechanism's per-element vocabulary (the closed `lane.class` enum, the class→default tier table, the prune-predicate names) is owned by [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md); these knobs carry only the project-level posture / override / threshold config the manifest composer resolves over that contract.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `lane_selection` | enum(`ask`\|`auto`) | `ask` | Whether init PROMPTS for the execution-profile posture (`ask` surfaces the minimal/auto/full dialogue) or silently takes the computed `auto` projection (`auto`). Validated by `validate_lane_selection`. Mirrors the `deep_lane` / `finalize_without_asking` ask/auto family. |
| `lane_prune_thresholds` | dict(`confidence_complete`, `linear_change_max_deliverables`) | `{confidence_complete: 95, linear_change_max_deliverables: 1}` | Tunable numeric thresholds the `auto` posture evaluates its prunable-element predicates against at manifest-compose time. `confidence_complete` (int 0–100) is the post-init confidence floor that prunes `refine`; `linear_change_max_deliverables` (int ≥ 1) is the deliverable-count ceiling that prunes the 4-plan decomposition element. The boolean predicates (`no_code_delta`, `footprint_no_lesson_component`) carry no threshold. Validated by `validate_lane_prune_thresholds` (exact key set; ranges enforced). |

**Per-element lane override** (`plan.<phase>.steps.<step>.lane`, value ∈ `off`\|`minimal`\|`auto`\|`full`\|`ask`, validated by `validate_lane_override`): pins any lane-participating element to a fixed posture cutoff via the same nested step-param channel finalize-step params use — `off` never runs it (a `derived-state`/`core` weakening additionally emits a correctness warning at compose time, but is honored), `minimal` force-keeps it in every posture, `auto`/`full` pin its tier, `ask` always surfaces it individually in the init dialogue. Absent by default — the shipped per-element default lives in each element's frontmatter `lane:` block, and `marshal.json` carries only the project / meta overrides.

**Flat finalize automation knobs (boolean, under `phase-6-finalize`):**

| Field | Default | Meaning |
|-------|---------|---------|
| `finalize_without_asking` | `true` | Auto-continue into finalize after execute. |
| `loop_back_without_asking` | `false` | Auto-re-enter on a finalize loop_back outcome. |

(`final_merge_without_asking` is NOT flat — it is a step-owned param nested under the `default:branch-cleanup` step; see the step-owned param tables below.)

**Step-owned params (nested under their owning step in the `phase-6-finalize.steps` keyed map):**

`default:sonar-roundtrip` (the `sonar_` prefix is dropped within the scoped object):

| Param | Type | Default | Meaning |
|-------|------|---------|---------|
| `touched_file_cleanup` | enum(`new_code_only`\|`touched_files_zero`) | `new_code_only` | Cleanup-scope for the Sonar roundtrip success criterion. `new_code_only` (lean default) anchors success on new-code issues == 0; `touched_files_zero` also sweeps pre-existing issues on touched files. Validated by `validate_sonar_touched_file_cleanup`. |
| `do_transition` | bool | `false` | Gate for the server-side SonarCloud dismissal path. `false` routes FALSE-POSITIVE / WON'T-FIX dispositions through in-code suppression; `true` re-enables `sonar_rest transition` dismissal. Consumed by triage Step 3c as the fall-through gate. |
| `ce_wait_timeout_seconds` | int | `600` | Budget (seconds) for the synchronous in-Python CE-readiness wait in `sonar.py fetch_findings` — sibling of the flat `checks_wait_timeout_seconds`; overridable by `--ce-wait-timeout`. |

`plan-marshall:automatic-review`: `review_bot_buffer_seconds` (int, default `180`) — max-wait ceiling for `pr wait-for-comments`. `default:branch-cleanup`: `pr_merge_strategy` (default `squash`), `final_merge_without_asking` (bool, default `false`), `auto_rebase_threshold` (default `no_overlap_only`).

**Access shape.** Read/write each FLAT knob through the standard `plan <phase> get/set --field <knob>` verb — e.g. `plan phase-6-finalize get --field qgate`, `plan phase-6-finalize get --field finalize_without_asking`. Read/write each STEP-OWNED param through the one-stop `plan phase-6-finalize step get/set --step-id {step} [--param {k} --value {v}]` verb against the marshal.json keyed-map serial form (the global-config default + wizard write target), or via the plan-local manifest snapshot `manage-execution-manifest step-params get/set` (the per-plan runtime read/override). See [§ Workflow: Phase-Local Run-at-all Gates and Automation Knobs](#workflow-phase-local-run-at-all-gates-and-automation-knobs).

**Default source.** The `Default` column above is not held in any centralized constant. Each param-owning step declares its params self-describingly in the `configurable:` block of its body-doc frontmatter; the finalize-step defaults seed (`get_default_config()`) materializes them by delegating each built-in step id through the `plan-marshall:extension-api:configurable_contract` parser (`resolve_step_defaults_optional`, ownerless steps → `null`). The parser is the single fail-loud source of truth for a valid step-param declaration — see [`extension-api` SKILL.md § Configurable step-param contract](../extension-api/SKILL.md#configurable-step-param-contract).

### Build-Queue Settings

The `build.queue` block lives under the top-level `build` block in marshal.json (peer to `build.map`, not under `plan.*`) because the build queue is a project-wide, cross-plan resource — every session bounds its concurrent builds against the same shared queue. Both keys are seeded into a fresh marshal.json by `init` and back-filled into existing projects by `sync-defaults`.

| Field | Default | Meaning |
|-------|---------|---------|
| `max_slots` | `5` | Number of concurrent build admissions the cross-session build queue grants before further requests are enqueued FIFO. Read by the build-queue admission primitive (`plan-marshall:manage-locks:build_queue`) via `build.queue.max_slots`; a missing block, missing key, or non-positive value falls back to `5`. |
| `max_retries` | `10` | Number of times the build wrapper re-polls a `blocked` admission before giving up. |

Edit both keys directly in marshal.json — they are operator-visible JSON integers at the top level.

---

## Standard Domains

> **Detailed reference**: See [standards/skill-domains.md](standards/skill-domains.md) for domain structure, profiles, and validation rules. See [standards/skill-domains-operations.md](standards/skill-domains-operations.md) for resolution commands and usage patterns.

### System Domain

The `system` domain contains execute-task skills and base skills applied to all tasks.

| Field | Purpose |
|-------|---------|
| `defaults` | Base skills loaded for all tasks (`plan-marshall:persona-plan-marshall-agent`) |
| `optionals` | Optional base skills available for selection |

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

### project get

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config project get \
  --field FIELD
```

`--field working_prefixes` returns the canonical closed set of allowed
working-branch prefixes (a flat JSON array of strings, default
`["feature/", "fix/", "chore/"]`), falling back to the `DEFAULT_PROJECT`
default when the key is absent from marshal.json.

### project set

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config project set \
  --field FIELD --value VALUE
```

Scalar fields (e.g. `default_base_branch`) take a plain value; the list-valued
field `working_prefixes` takes a JSON array of strings that round-trips through
`get`. A non-array value (or an array containing a non-string item) is rejected
with `error_type: invalid_type`.

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

The scalar `set` verb rejects the keyed step-map field of `phase-5-execute`
(`--field verification_steps`) and `phase-6-finalize` (`--field steps`) with a
structured error and no mutation — those fields are keyed step-maps, not
scalars. Use `set-steps` / `add-step` / `remove-step` to manage the step map
and `step get` / `step set` for a step's nested params.

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

### plan phase-6-finalize step get / plan phase-5-execute step get

Returns the complete nested param object for a step in a single call against the marshal.json keyed map.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-6-finalize step get \
  --step-id STEP_ID
```

### plan phase-6-finalize step set / plan phase-5-execute step set

Writes one step-owned param into the step's nested object (value-coerced).

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-6-finalize step set \
  --step-id STEP_ID --param PARAM --value VALUE
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

### effort set

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort set \
  --scope {phase}.{role}|plan --level LEVEL
```

Surgical per-scope writer. `--scope {phase}.{role}` (e.g. `phase-6-finalize.verification-feedback`) writes one nested effort scope, preserving sibling sub-keys (a pre-existing scalar `effort` string is normalised into an object first). `--scope plan` writes the `plan.effort` plan-wide scalar. Unknown phase/role and invalid `--level` are rejected.

### coverage read

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage read \
  [--role ROLE] [--phase PHASE] [--default]
```

### coverage resolve

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage resolve \
  [--role ROLE] [--phase PHASE] [--default]
```

### coverage expand

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand \
  --thoroughness THOROUGHNESS --scope SCOPE
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

### list-recipes

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes
```

### resolve-recipe

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-recipe \
  --recipe RECIPE_KEY
```

### recipe-match

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config recipe-match \
  --request-text REQUEST_TEXT [--threshold 0.6]
```

Tier 1 recipe-match: scores free-form `--request-text` against the live recipe registry using the shared `recipe_scoring` core (the same keyword/intent-overlap matcher the lesson auto-suggest path consumes). Returns the ranked `matches[]` (each with `key`, `name`, `skill`, `domain`, `scope`, `source`, `confidence`, `breakdown`), a `top_match`, and a `meets_auto_route_threshold` boolean (`true` only when the top match's confidence is `>= --threshold`, default `0.6` — the keyword-only scoring ceiling for free-form requests, so a perfect keyword match exactly meets the bar). Returns `status: success` with empty `matches` when nothing clears the minimum-confidence floor.

The verb is **heuristic-first**: it performs no LLM call and no plan-scoped read — only the free-form request text drives scoring (no plan domain/scope is available, so keyword overlap is the sole signal). The bounded LLM fallback for ambiguous matches is **orchestrator-driven** (phase-1-init), not part of this script — mirroring how `change-type-heuristic` and `planning-lane route` keep the LLM out of the script body.

Output TOON shape:

```toon
status: success
request_tokens[N]: [token, ...]
recipes_evaluated: N
threshold: 0.6
matches[N]{key,name,skill,domain,scope,source,confidence,breakdown}:
  ...
count: N
top_match:
  key: ...
  confidence: ...
meets_auto_route_threshold: true | false
```

### aspect-classify

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config aspect-classify \
  --request-text REQUEST_TEXT [--threshold 0.7]
```

Request-aspect classifier: tokenizes free-form `--request-text` via the shared `recipe_scoring.tokenize` and scores the token overlap against three fixed keyword tables — `analysis`, `planning`, and `implementation`. The higher of analysis/planning is the candidate aspect; it is accepted only when its `_overlap_score` confidence clears `>= --threshold` (default `0.7`) AND beats the implementation overlap. Otherwise the verb returns the safe `implementation` fallback, which keeps every build / quality-gate / test gate in the composed manifest. The caller (phase-1-init) persists the resolved `aspect`; the execution-manifest composer drops build / quality-gate / test steps when the aspect is `analysis` or `planning` (`drops_build_steps: true`).

The `--threshold` here is **independent of** the `recipe-match` verb's `--threshold` and of the `auto_route_recipe_threshold` config knob. Those caps at `0.6` because plan-domain/scope blending is unavailable; `aspect-classify` uses a pure request-token overlap fraction (`_overlap_score`, range `0.0–1.0`) with NO `0.6` ceiling, so its `0.7` default is reachable and intentional. Do not conflate the two thresholds.

The verb is **heuristic-first**: it performs no LLM call and no plan-scoped read — only the free-form request text drives scoring. The bounded LLM fallback for genuinely ambiguous requests is **orchestrator-driven** (phase-1-init), not part of this script — mirroring `change-type-heuristic`'s heuristic-first / conservative-default contract.

Output TOON shape:

```toon
status: success
request_tokens[N]: [token, ...]
threshold: 0.7
aspect: analysis | planning | implementation
confidence: 0.0-1.0
drops_build_steps: true | false
scores:
  analysis: 0.0-1.0
  planning: 0.0-1.0
  implementation: 0.0-1.0
breakdown:
  analysis:
    score: 0.0-1.0
    matched_keywords[N]: [keyword, ...]
  planning:
    score: 0.0-1.0
    matched_keywords[N]: [keyword, ...]
  implementation:
    score: 0.0-1.0
    matched_keywords[N]: [keyword, ...]
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

### build-map seed

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed \
  [--force]
```

`--force` clears any existing `build_map` and re-derives a clean one from the current project state, bypassing the write-once guard.

### build-map read

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map read
```

### build-map drift

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map drift
```

Read-only diff of the persisted `build.map` against the live derivation. Returns `in_sync` plus per-domain `added_globs` / `removed_globs`; never mutates `marshal.json`.

### normalize-keys

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config normalize-keys
```

Re-writes `marshal.json` with the canonical top-level key order (reuses the `save_config` writer). Silent and idempotent — an already-canonical file is left byte-stable.

### build-decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-decision \
  --command COMMAND --plan-id PLAN_ID
```

Returns a `build` / `not_necessary` verdict for `COMMAND` against `PLAN_ID`'s live footprint. `--audit-plan-id` is accepted as an alias for `--plan-id`.

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error | Cause | Resolution |
|-------|-------|------------|
| `not_initialized` | marshal.json missing | Run `/marshall-steward` |
| `invalid_domain` | Domain not in skill_domains | Check domain name or run `/marshall-steward` |
| `skill_domains not configured` | No domains in marshal.json | Run `/marshall-steward` |
| `invalid_field` | Unknown field for phase/noun | Check field reference table above |
| keyed step-map `set --field` rejection | `set --field verification_steps` (phase-5-execute) or `set --field steps` (phase-6-finalize) — those fields are keyed step-maps, not scalars | Use `set-steps` / `add-step` / `remove-step`, or `step set` for a step's nested params |
| `skill_not_found` | Skill not in domain defaults/optionals | Check with `validate --domain --skill` |

---

## Related

- [standards/config-design-principles.md](standards/config-design-principles.md) — Governance rules for what belongs in `marshal.json` and how config fields change (ownership, placement, anti-speculation, lossless migration)
- `manage-architecture` — Consumes configuration for project analysis
- `marshall-steward` — Interactive configuration wizard
- `extension-api` — Build system detection uses config
