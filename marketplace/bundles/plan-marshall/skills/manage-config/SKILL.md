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
  - plan.phase-5-execute.per_task_budget_reserve_tokens
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
  plan phase-5-execute set --field commit_and_push --value false

# Select the per-deliverable build depth — enum: off | compile-only | compile+scoped-test | full
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field per_deliverable_build --value full
```

**phase-5-execute per-deliverable build field:**

| Field | Type | Default | Semantics |
|-------|------|---------|-----------|
| `per_deliverable_build` | enum(`off`\|`compile-only`\|`compile+scoped-test`\|`full`) | `compile+scoped-test` | Build depth phase-5-execute runs at each per-deliverable chain-tail point (Step 10). `off` skips the per-deliverable build entirely (the end-of-phase quality sweep is the only build); `compile-only` resolves the changed module and runs compile only; `compile+scoped-test` additionally runs scoped `module-tests` for the changed module; `full` runs whole-tree `quality-gate` per deliverable (legacy behavior, opt-in only). Read by phase-5-execute per-deliverable. Invalid values are rejected by the config setter. |

**Symmetric auto-continuation knobs:** the forward (`finalize_without_asking`) and reverse (`loop_back_without_asking`) auto-continuation knobs, together with `auto_merge_after_ci`, are flat knobs under `plan.phase-6-finalize` — read/written via the standard `manage-config plan phase-6-finalize get/set --field <knob>` access shape.

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

### Coverage two-knob configuration

Coverage is a two-dial contract — `thoroughness` (T1–T5) × `scope` (change-set…overall) — orthogonal to the `effort` model-tier dial. A per-phase override lives under the phase entry's `coverage` key; the plan-wide fallback is `plan.coverage` (seeded `inherit/inherit`). The `read`/`resolve` verbs mirror the `effort` resolver's lookup shape, resolving each field independently from `marshal.json` only (the project-DEFAULT tier — no per-plan tier), and enforcing the scope↔thoroughness coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) at lookup time. See [`dev-agent-behavior-rules/standards/thoroughness.md`](../dev-agent-behavior-rules/standards/thoroughness.md) § Coupling Constraint.

`coverage`'s consumers are the broad-pass components that implement the [coverage-gathering contract](../dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — wide audits, compliance sweeps, simplification/refactor campaigns, pre-submission review. Each gathers a `(thoroughness, scope)` cell from the user at invocation, expands it via `coverage expand`, persists the identifier + expanded instruction in `status.json` metadata, and consumes the expanded instruction to govern its breadth/depth. `coverage resolve` is the project-default tier consulted when no per-invocation cell was gathered.

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

## Workflow: Phase-Local Run-at-all Gates and Automation Knobs

**Pattern**: Read-Process

The lifecycle run-at-all gates and automation knobs are flat knobs under their owning phase — read/written through the standard `plan <phase> get/set --field <knob>` verb. Each gate takes `auto|always|never` (validated by `validate_run_at_all`); the automation knobs are boolean. Distribution:

| Knob | Location | Read via |
|------|----------|----------|
| `deep_lane` | `plan.phase-1-init` | `plan phase-1-init get --field deep_lane` |
| `escalation` | `plan.phase-1-init` | `plan phase-1-init get --field escalation` |
| `revalidation` | `plan.phase-2-refine` | `plan phase-2-refine get --field revalidation` |
| `qgate` (planning) | `plan.phase-3-outline` | `plan phase-3-outline get --field qgate` |
| `finalize_without_asking` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field finalize_without_asking` |
| `loop_back_without_asking` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field loop_back_without_asking` |
| `auto_merge_after_ci` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field auto_merge_after_ci` |
| `self_review` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field self_review` |
| `qgate` (finalize) | `plan.phase-6-finalize` | `plan phase-6-finalize get --field qgate` |
| `plugin_doctor` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field plugin_doctor` |
| `simplify` | `plan.phase-6-finalize` | `plan phase-6-finalize get --field simplify` |

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

The `build.map` block in `marshal.json` is the file-to-build contract: a domain-keyed inventory of `{glob, role, build_class}` entries that maps every changed path to the build action it requires. It lives at the top-level `build.map` block (its owning block, peer to `build.queue`) and is populated from the registered domain extensions with write-once semantics — an existing seed survives a re-seed so user corrections are preserved. The seeded globs are **explicit `(pattern, role)` routes**: each extension declares its routes directly via `classify_globs()` (single-`*` fnmatch globs, never recursive `**`), and the `script-shared` route collector gathers them verbatim. A separate git-tracked completeness validator scans `git ls-files` and flags any tracked source file no declared route covers, so a forgotten production module surfaces rather than silently classifying to no build. There is no separate override layer; corrections are made directly to the seeded entries.

**Applicability scoping.** The seed includes a domain's routes only when that domain applies to the project. `aggregate_build_map()` consults each domain's owning extension's `applies_to_module()` against the discovered project modules and keeps the domain's routes only when `applies_to_module()` reports `applicable: True` for at least one discovered module — the same applicability predicate architecture enrichment uses. A Python-only project therefore never receives `java` / `oci` / `javascript` routes merely because those bundles are installed. Because applicability is resolved against discovered modules, the seed is **post-architecture-only**: when module discovery yields no modules (architecture not yet discovered) the aggregation is empty.

**Seed point.** The build map is **not** populated at `init` or by `sync-defaults` — `get_default_config()` does not include a `build_map` block, so neither the `init` write nor the `sync-defaults` deep-merge seeds it. The wizard's Step 8b (`build-map seed`, run after architecture discovery) is the **sole authoritative seed point**; the write-once guard makes that first explicit seed authoritative. Re-run `build-map seed` whenever a domain extension is added or updated.

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
| `configure-execute-task-skills` | Auto-discover profiles and register execute-task skills |
| `resolve-execute-task-skill` | `--profile` (resolve execute-task skill for profile) |
| `ext-defaults` | get, set, set-default, list, remove |
| `system` | retention get, retention set |
| `project` | `get/set` (`default_base_branch`, `working_prefixes`) |
| `plan` | `{phase} get/set` (incl. run-at-all gates + finalize automation knobs), set-steps, add-step, remove-step, set-max-iterations |
| `ci` | get, get-provider, get-tools, get-command, set-provider, set-tools, persist |
| `build-map` | `seed` (re-seed `build.map` from applicable extensions, write-once; `--force` clears + re-derives), `read` (effective map from `build.map`, fail-closed when absent) |
| `build-decision` | `--command --plan-id` (centralized build-necessity verdict: `build` / `not_necessary`; `not_necessary` carries a log-friendly `reason`) |
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
      "escalation": "auto"
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking",
      "revalidation": "auto"
    },
    "phase-3-outline": {
      "plan_without_asking": false,
      "qgate": "auto"
    },
    "phase-5-execute": {
      "commit_and_push": true,
      "max_iterations": 5,
      "per_deliverable_build": "compile+scoped-test",
      "steps": ["quality_check", "build_verify"]
    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 180,
      "finalize_without_asking": true,
      "loop_back_without_asking": false,
      "auto_merge_after_ci": true,
      "self_review": "auto",
      "qgate": "auto",
      "plugin_doctor": "auto",
      "simplify": "auto",
      "steps": [
        "commit_push", "create_pr", "automated_review",
        "sonar_roundtrip", "lessons_capture",
        "branch_cleanup", "archive"
      ]
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
| `qgate` | `phase-3-outline` | Whether the planning-time q-gate validation runs (deep-lane outline dispatch). |
| `self_review` | `phase-6-finalize` | Whether the pre-submission structural + cognitive self-review runs (manifest finalize step-selection). |
| `qgate` | `phase-6-finalize` | Whether finalize re-captures blocking findings. **Highest-risk gate** — `never` can mask real build/test failures. |
| `plugin_doctor` | `phase-6-finalize` | Whether structural marketplace lint runs before push. |
| `simplify` | `phase-6-finalize` | Whether the holistic post-implementation simplification sweep (`finalize-step-simplify`) runs. `always` forces it in even when the composer's `simplify_inactive` pre-filter would drop it; `never` skips it; `auto` defers to that pre-filter. |

**Finalize automation knobs (boolean, under `phase-6-finalize`):**

| Field | Default | Meaning |
|-------|---------|---------|
| `finalize_without_asking` | `true` | Auto-continue into finalize after execute. |
| `loop_back_without_asking` | `false` | Auto-re-enter on a finalize loop_back outcome. |
| `auto_merge_after_ci` | `true` | Auto-merge the PR after CI passes. |

**Access shape.** Read/write each knob through the standard `plan <phase> get/set --field <knob>` verb — e.g. `plan phase-6-finalize get --field qgate` or `plan phase-6-finalize get --field finalize_without_asking`. See [§ Workflow: Phase-Local Run-at-all Gates and Automation Knobs](#workflow-phase-local-run-at-all-gates-and-automation-knobs).

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
| `skill_not_found` | Skill not in domain defaults/optionals | Check with `validate --domain --skill` |

---

## Related

- [standards/config-design-principles.md](standards/config-design-principles.md) — Governance rules for what belongs in `marshal.json` and how config fields change (ownership, placement, anti-speculation, lossless migration)
- `manage-architecture` — Consumes configuration for project analysis
- `marshall-steward` — Interactive configuration wizard
- `extension-api` — Build system detection uses config
