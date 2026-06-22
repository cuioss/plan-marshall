# Marshal.json Reference

Central reference for all extension-related configuration paths in `marshal.json` and `run-configuration.json`.

## Extension Configuration (marshal.json)

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `skill_domains.{key}.bundle` | Auto (skill-domains configure) | Runtime (extension resolution) | Core |
| `skill_domains.{key}.domain.key` | `get_skill_domains()` | Runtime | Core |
| `skill_domains.{key}.domain.name` | `get_skill_domains()` | Display | Core |
| `skill_domains.{key}.profiles` | `get_skill_domains()` | Skill loading | Core |
| `skill_domains.{key}.outline_skill` | `provides_outline_skill()` | phase-3-outline | [ext-point-outline.md](ext-point-outline.md) |
| `skill_domains.{key}.workflow_skill_extensions.triage` | `provides_triage()` | phase-5-execute, phase-6-finalize | [ext-point-triage.md](ext-point-triage.md) |
| `build.map` | `classify_globs()` + `classify_build_class()` (seeded, write-once, required + always seeded) | architecture derive-verification; phase-6-finalize pre-push-quality-gate activation | Core |
| `extension_defaults.*` | `config_defaults()` | Various (write-once semantics) | Core |

## Plan Phase Configuration (marshal.json)

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `plan.phase-1-init.init_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-2-refine.confidence_threshold` | User config | phase-2-refine | - |
| `plan.phase-2-refine.compatibility` | User config | phase-2-refine, phase-3-outline | - |
| `plan.phase-3-outline.plan_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-4-plan.execute_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-5-execute.commit_and_push` | User config | phase-5-execute, phase-6-finalize | - |
| `plan.phase-5-execute.verification_steps` (keyed-map serial form) | Built-in + project `verify-step-*` skills | phase-4-plan, phase-5-execute | - |
| `plan.phase-5-execute.max_iterations` | User config | phase-5-execute | - |
| `plan.phase-6-finalize.steps` (keyed-map serial form; each value is the step's nested param object) | Built-in + project `finalize-step-*` skills + bundle-optional | phase-6-finalize | - |
| `plan.phase-6-finalize.max_iterations` | User config | phase-6-finalize (loop-back ceiling) | - |
| `plan.phase-6-finalize.checks_wait_timeout_seconds` (flat phase-level) | User config | tools-integration-ci (CI-completion polling timeout) | - |

## Canonical `steps` / `verification_steps` Serial Form (keyed map)

`plan.phase-5-execute.verification_steps` and `plan.phase-6-finalize.steps` serialize on disk as an **id-keyed map** (a JSON object keyed by step id), with key insertion order as the execution order. Each value is the step's nested param object — `{}` for a config-less step, a `{ param: value, … }` object for a param-owning step. This is the canonical serial form every `.plan/marshal.json` MUST follow — it is the shape `init` seeds, `sync-defaults` back-fills, and the wizard writes, and it is the sole shape the reader accepts.

Three structural rules define the serial form:

1. **A keyed map, not a list.** The container is a JSON object keyed by step id. Key insertion order is the execution order. Each key identifies one step (`default:commit-push`, `default:branch-cleanup`, a `project:` step, or a fully-qualified `bundle:skill` step). A list value is not a valid on-disk form — the reader returns no step map for it.
2. **Config-less step → `{}`; param-bearing step → nested param object.** A step that owns no params maps to an empty `{}` object. A step that owns params maps to a `{ param: value, … }` object — its value is the nested param object. A param consumed by exactly one step lives in that step's nested object, never as a flat phase-level sibling. Example: `final_merge_without_asking` is a param of `default:branch-cleanup`, so it nests inside `{ "default:branch-cleanup": { … } }`, NOT under `phase-6-finalize` directly. Read/write step-owned params via the one-stop `manage-config plan {phase} step get/set --step-id {id}` verb (global default + wizard target) or `manage-execution-manifest step-params get/set` (per-plan runtime read/override).
3. **Config-less steps map to `{}`.** A config-less step's value is an empty `{}` object. The reader coerces any non-dict per-step value (`null`, the TOON-round-tripped `''`) back to `{}` internally, so downstream consumers see a uniform `{}` for a config-less step.

### Canonical serial form (illustrative)

```json
{
  "plan": {
    "phase-5-execute": {
      "verification_steps": {
        "default:verify:quality-gate": {},
        "default:verify:module-tests": {}
      }
    },
    "phase-6-finalize": {
      "steps": {
        "default:commit-push": {},
        "default:automated-review": {
          "review_bot_buffer_seconds": 180
        },
        "default:sonar-roundtrip": {
          "touched_file_cleanup": "new_code_only",
          "do_transition": false,
          "ce_wait_timeout_seconds": 600
        },
        "default:branch-cleanup": {
          "pr_merge_strategy": "squash",
          "final_merge_without_asking": false,
          "auto_rebase_threshold": "no_overlap_only"
        }
      }
    }
  }
}
```

Notes on the example:

- `default:commit-push` and the two `verify:*` steps own no params, so each maps to an empty `{}` object.
- `default:automated-review`, `default:sonar-roundtrip`, and `default:branch-cleanup` own params, so each maps to its nested param object. For `default:sonar-roundtrip` the `sonar_` prefix is dropped inside the scoped object.
- Param **defaults** are NOT held in any centralized constant. Each param-owning step declares its own params (`key`, `default`, `description`) in the `configurable:` block of its body-doc frontmatter; the parser (`plan-marshall:extension-api:configurable_contract`) materializes them. See [`manage-config/SKILL.md` § Phase-Local Run-at-all Gates and Automation Knobs](../../manage-config/SKILL.md) and [`extension-api/SKILL.md` § Configurable step-param contract](../SKILL.md#configurable-step-param-contract).

### Reader

The reader accepts the canonical keyed map on disk, normalizing each value to the internal id-keyed dict (`{ step_id: param-object }`, `{}` for config-less steps). The read-side normalizers are `_steps_map` (in `_cmd_quality_phases.py`, the `manage-config` write/read verbs) and `_read_marshal_phase_step_map` (in `manage-execution-manifest.py`, the manifest composer); both consume the keyed map directly and every config write verb persists it directly. The keyed map is the sole on-disk shape both read and written — there is no list / dual-form tolerance.

> **Distinct surface — do not conflate.** The per-plan execution-MANIFEST `step_params` block (`body[phase].step_params[step_id]`, persisted in `execution.toon`, read/written via `manage-execution-manifest step-params get/set`) is an id-keyed **dict** — internal plumbing for per-plan param overrides, documented in [`manage-execution-manifest`'s manifest schema](../../manage-execution-manifest/standards/manifest-schema.md). It is NOT the marshal.json serial form. The keyed serial form governs `steps` / `verification_steps` in **marshal.json**; the manifest `step_params` snapshot is a separate dict surface.

### Consumer-repo target

Consumer `.plan/marshal.json` files (e.g. plan-marshall's own consumer repos) MUST carry the keyed-map serial form: `steps` / `verification_steps` as an id-keyed object — config-less steps as `{}`, param-owning steps as their nested param object. Preserve execution order (key insertion order) and each repo's operator customizations; do not strip them.

## Run-at-all Gates and Finalize Automation Knobs (marshal.json)

The lifecycle run-at-all gates and the two flat finalize automation knobs are flat phase-local knobs under their owning phase — `deep_lane` / `escalation` under `plan.phase-1-init`, `revalidation` under `plan.phase-2-refine`, `qgate` under `plan.phase-3-outline`, and the finalize `qgate` gate plus the two flat automation knobs (`finalize_without_asking` / `loop_back_without_asking`) under `plan.phase-6-finalize`. Read the flat knobs at runtime via `manage-config plan <phase> get --field <knob>`. (Per rule 2 of the keyed-map serial-form section above, the finalize `self_review` and `simplify` gates and `final_merge_without_asking` / `drop_review_on_scope_gate` are NOT flat — they are step-owned params nested inside their owning step's value in the keyed map; see the step-owned param rows below.) See [`manage-config/SKILL.md`](../../manage-config/SKILL.md) § "Phase-Local Run-at-all Gates and Automation Knobs" for the full schema.

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `plan.phase-1-init.deep_lane` | User config | phase-1-init lane router | - |
| `plan.phase-1-init.escalation` | User config | phase-1-init escalation ratchet | - |
| `plan.phase-2-refine.revalidation` | User config | light lane + deep refine | - |
| `plan.phase-3-outline.qgate` | User config | deep-lane outline dispatch | - |
| `plan.phase-6-finalize.steps['project:finalize-step-pre-submission-self-review'].self_review` (step-owned param; read via `manage-execution-manifest step-params get`) | User config | manage-execution-manifest (finalize selection) | - |
| `plan.phase-6-finalize.qgate` | User config | manage-execution-manifest (finalize selection) | - |
| `plan.phase-6-finalize.steps['default:finalize-step-simplify'].simplify` (step-owned param; read via `manage-execution-manifest step-params get`) | User config | manage-execution-manifest (finalize selection) | - |
| `plan.phase-6-finalize.steps['project:finalize-step-pre-submission-self-review'].drop_review_on_scope_gate` (step-owned param; read via `manage-execution-manifest step-params get`) | User config | manage-execution-manifest (scope-gated review drop) | - |
| `plan.phase-6-finalize.finalize_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-6-finalize.loop_back_without_asking` | User config | phase-6-finalize, plan-marshall orchestrator | - |
| `plan.phase-6-finalize.steps['default:branch-cleanup'].final_merge_without_asking` (step-owned param; read via `manage-execution-manifest step-params get`) | User config | phase-6-finalize (branch-cleanup pre-merge gate) | - |
| `plan.phase-6-finalize.steps['default:automated-review'].review_bot_buffer_seconds` (step-owned param; read via `manage-execution-manifest step-params get`) | User config | phase-6-finalize / workflow-pr-doctor (review-bot comment wait) | - |

## Project Configuration (marshal.json)

Project-level settings under the `project.*` block — persist across plans, seeded by `init`, back-filled into existing projects by `sync-defaults`.

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `project.default_base_branch` | User config (`marshall-steward`) | phase-1-init (references.base_branch seed) | - |
| `project.working_prefixes` | User config | marshall-steward (branch-prefix validation), structural branch-prefix coverage test | - |

## Build Configuration (run-configuration.json)

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `commands.{tool}:{cmd}.timeout_seconds` | Timeout learning | Build execution | [ext-point-build.md](ext-point-build.md) |
| `{tool}.acceptable_warnings` | User config | check-warnings | [ext-point-build.md](ext-point-build.md) |

## Project Architecture (per-module layout under `.plan/architecture/`)

The architecture cache is split: a top-level `_project.json` declares the canonical
module set and project-wide facts, and each entry in `_project.json["modules"]`
has its own subdirectory `<module>/` containing `derived.json` (raw discovery
output) and, after LLM enrichment, `enriched.json`. `_project.json["modules"]`
is the single source of truth — orphan subdirectories are ignored.

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `_project.json["modules"]` | `discover_modules()` (canonicalised) | phase-4-plan, phase-5-execute | [ext-point-build.md](ext-point-build.md) |
| `<module>/derived.json` (raw module facts) | `discover_modules()` | phase-4-plan, phase-5-execute | [ext-point-build.md](ext-point-build.md) |
| `<module>/derived.json` `commands` | `discover_modules()` | Architecture resolve | [ext-point-build.md](ext-point-build.md) |
| `<module>/enriched.json` (LLM-enriched view) | manage-architecture enrichment | phase-3-outline, phase-4-plan | [ext-point-build.md](ext-point-build.md) |

## Runtime-Only (Not Persisted)

| Data | Discovery | Used By | Extension Point Doc |
|------|-----------|---------|---------------------|
| Recipe list | `provides_recipes()` + project skills | `/plan-marshall action=recipe` | [ext-point-recipe.md](ext-point-recipe.md) |
| Provider declarations | `*_provider.py` scan | `manage-providers` | [ext-point-provider.md](ext-point-provider.md) |

## Credential Storage

Credentials are stored separately in `.plan/credentials/` (not in marshal.json). See [ext-point-provider.md](ext-point-provider.md) for the discovery and storage convention.

## Config-contract sweep coverage

The `configurable` step-param contract (each param-owning step declares its own `key` / `default` / `description`, materialized by `plan-marshall:extension-api:configurable_contract`) was rolled out for the **phase-6-finalize step-owned params**. This section surveys the remaining centralized-default clusters, id-keyed param maps, and default/description splits across `marketplace/bundles/**` and classifies each for contract adoption. The survey is analysis-only — none of these surfaces are mutated by this plan; the table records the rollout direction without expanding scope.

Classification key:

- **adopt-now** — a genuine step-owned param cluster with a default/description split that the `configurable` contract directly fits; a future migration candidate.
- **adopt-later** — could be expressed via a self-describing contract eventually, but lacks a step owner today or would need a contract extension; defer until a step-owner emerges.
- **not-a-fit** — phase-level / project-level / cross-plan config that is NOT a step-owned param; the contract does not apply by construction.

| Cluster (source) | Kind | Classification | Rationale |
|------------------|------|----------------|-----------|
| `DEFAULT_PLAN_FINALIZE['steps'][*]` step-owned params (`_config_defaults.py`) | keyed-map serial form + nested params | **adopted** | Each finalize step declares its params via the `configurable` contract (`_FINALIZE_STEP_PARAMS` deleted); the seed materializes the canonical keyed map directly (`{step_id: {params}}`, `{}` for config-less steps). |
| `DEFAULT_PLAN_INIT` knobs — `deep_lane`, `escalation`, `init_without_asking`, `branch_strategy`, `use_worktree`, `effort` (`_config_defaults.py`) | flat phase knobs | **not-a-fit** | Phase-level run-at-all gates and lifecycle knobs consumed by the init lane router / orchestrator — no single owning step, decision-machinery inputs not step-body params. |
| `DEFAULT_PLAN_REFINE` knobs — `confidence_threshold`, `compatibility`, `simplicity`, `revalidation`, `effort` (`_config_defaults.py`) | flat phase knobs | **not-a-fit** | Phase-level refine knobs / run-at-all gate; consumed by the light-lane + deep-refine pass, not by a step body. |
| `DEFAULT_PLAN_OUTLINE` knobs — `plan_without_asking`, `qgate`, `effort` (`_config_defaults.py`) | flat phase knobs | **not-a-fit** | Phase-level outline knobs / run-at-all gate; `qgate` is decision machinery, deliberately kept flat. |
| `DEFAULT_PLAN_PLAN` knobs — `execute_without_asking`, `effort` (`_config_defaults.py`) | flat phase knobs | **not-a-fit** | Phase-level orchestrator gates; no step owner. |
| `DEFAULT_PLAN_EXECUTE.cost_size_token_table` (`_config_defaults.py`) | size→token map with a dedicated validator (`validate_cost_size_token_table`) | **adopt-later** | A self-describing default+validator cluster, but it is phase-wide bin-packer tuning consumed by `pack-envelopes`, not owned by any single execute step; defer until/unless a step-owner surfaces. |
| `DEFAULT_PLAN_EXECUTE.per_envelope_budget_tokens` (`_config_defaults.py`) | flat phase scalar | **not-a-fit** | Phase-level bin-packer budget consumed by `pack-envelopes`; not a step-body param. |
| `DEFAULT_PLAN_EXECUTE.per_deliverable_build` (`_config_defaults.py`) | list of `default:verify:{canonical}` ids + prefix validator | **adopt-later** | Has a self-describing validator (`validate_per_deliverable_build`), but the value is a phase-level verify-step list, not a step-owned param object; revisit if verify steps gain owned params. |
| `BUILT_IN_VERIFY_STEPS` + `BUILT_IN_VERIFY_STEP_DESCRIPTIONS` (`_config_defaults.py`) | parallel id-list + id→description map (default/description split) | **adopt-later** | A textbook default/description split, but verify steps are currently param-less (their value is `{}`); the `configurable` contract becomes worthwhile only once a verify step declares owned params. |
| `BUILT_IN_FINALIZE_STEP_DESCRIPTIONS` / `OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS` (`_config_defaults.py`) | id→description maps | **adopt-now** | Finalize steps already declare params via the contract; folding their human-readable descriptions into the same per-step `configurable` block would complete the self-describing model and remove the last centralized description map. |
| `DEFAULT_BUILD_QUEUE` — `max_slots`, `max_retries`, `upper_limit_seconds` (`_config_defaults.py`) | flat `build.queue` block | **not-a-fit** | Project-wide, cross-plan build-queue resource under top-level `build.*` (peer to `build.map`); not a plan step param. |
| `build.map` (`classify_globs()` / `classify_build_class()`) | seeded write-once glob→build-class map | **not-a-fit** | Project architecture data, not a step-owned param; consumed by architecture derive-verification. |
| `DEFAULT_SYSTEM_RETENTION` / `DEFAULT_PROJECT` / `DEFAULT_SYSTEM_DOMAIN` (`_config_defaults.py`) | system/project config blocks | **not-a-fit** | Project- and system-scoped config (skill domains, retention, base branch); no step owner. |
| `BUILD_SYSTEM_DEFAULTS` (`_config_defaults.py`) | build-system detection defaults | **not-a-fit** | Build-system abstraction defaults, not plan step params. |
| run-configuration.json `commands.{tool}:{cmd}.timeout_seconds` / `{tool}.acceptable_warnings` | learned/user build knobs | **not-a-fit** | Build-execution tuning in `run-configuration.json`, outside the plan step model. |
| `manage-locks` queue / mutex tunables | lock-primitive constants | **not-a-fit** | Cross-session coordination primitives, not plan config. |
| `manage-metrics` accumulator / boundary knobs | metrics-pipeline constants | **not-a-fit** | Internal metrics-pipeline constants, not user-facing step params. |

**Rollout direction:** the only **adopt-now** surface is the finalize-step description maps (fold descriptions into the per-step `configurable` block alongside the already-migrated params). The two **adopt-later** surfaces (`cost_size_token_table`, the verify-step default/description split) become contract candidates only if/when a step owner emerges for them. Every other cluster is **not-a-fit** by construction — phase-level gates, project/system config, build-queue/architecture data, and pipeline-internal constants are not step-owned params. These observations are NOT folded into this plan; lean scope keeps this plan to the finalize-step contract.
