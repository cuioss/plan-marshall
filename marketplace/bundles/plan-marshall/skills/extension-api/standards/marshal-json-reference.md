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
| `extension_defaults.*` | `config_defaults()` | Various (write-once semantics) | Core |

## Plan Phase Configuration (marshal.json)

| Path | Set By | Used By | Extension Point Doc |
|------|--------|---------|---------------------|
| `plan.phase-2-refine.confidence_threshold` | User config | phase-2-refine | - |
| `plan.phase-2-refine.compatibility` | User config | phase-2-refine, phase-3-outline | - |
| `plan.phase-3-outline.plan_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-4-plan.execute_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-5-execute.commit_strategy` | User config | phase-5-execute | - |
| `plan.phase-5-execute.steps` | Built-in + `provides_verify_steps()` | phase-4-plan, phase-5-execute | [ext-point-verify-steps.md](ext-point-verify-steps.md) |
| `plan.phase-5-execute.finalize_without_asking` | User config | plan-marshall orchestrator | - |
| `plan.phase-5-execute.verification_max_iterations` | User config | phase-5-execute | - |
| `plan.phase-6-finalize.steps` | Built-in + `provides_finalize_steps()` | phase-6-finalize | [ext-point-finalize-steps.md](ext-point-finalize-steps.md) |

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
