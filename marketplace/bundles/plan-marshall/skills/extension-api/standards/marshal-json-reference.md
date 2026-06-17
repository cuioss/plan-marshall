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
| `plan.phase-5-execute.verification_steps` (id-keyed map) | Built-in + `provides_verify_steps()` | phase-4-plan, phase-5-execute | [ext-point-verify-steps.md](ext-point-verify-steps.md) |
| `plan.phase-5-execute.max_iterations` | User config | phase-5-execute | - |
| `plan.phase-6-finalize.steps` (id-keyed map; step-owned params nest under each step) | Built-in + `provides_finalize_steps()` | phase-6-finalize | [ext-point-finalize-steps.md](ext-point-finalize-steps.md) |
| `plan.phase-6-finalize.max_iterations` | User config | phase-6-finalize (loop-back ceiling) | - |
| `plan.phase-6-finalize.checks_wait_timeout_seconds` (flat phase-level) | User config | tools-integration-ci (CI-completion polling timeout) | - |

## Run-at-all Gates and Finalize Automation Knobs (marshal.json)

The lifecycle run-at-all gates and the two flat finalize automation knobs are flat phase-local knobs under their owning phase — `deep_lane` / `escalation` under `plan.phase-1-init`, `revalidation` under `plan.phase-2-refine`, `qgate` under `plan.phase-3-outline`, and the finalize gates (`self_review` / `qgate` / `simplify`) plus the two flat automation knobs (`finalize_without_asking` / `loop_back_without_asking`) under `plan.phase-6-finalize`. Read at runtime via `manage-config plan <phase> get --field <knob>`. (`final_merge_without_asking` is NOT flat — it is a step-owned param of `default:branch-cleanup`; see the step-owned param rows below.) See [`manage-config/SKILL.md`](../../manage-config/SKILL.md) § "Phase-Local Run-at-all Gates and Automation Knobs" for the full schema.

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `plan.phase-1-init.deep_lane` | User config | phase-1-init lane router | - |
| `plan.phase-1-init.escalation` | User config | phase-1-init escalation ratchet | - |
| `plan.phase-2-refine.revalidation` | User config | light lane + deep refine | - |
| `plan.phase-3-outline.qgate` | User config | deep-lane outline dispatch | - |
| `plan.phase-6-finalize.self_review` | User config | manage-execution-manifest (finalize selection) | - |
| `plan.phase-6-finalize.qgate` | User config | manage-execution-manifest (finalize selection) | - |
| `plan.phase-6-finalize.simplify` | User config | manage-execution-manifest (finalize selection) | - |
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
