# Model Roles — Role Registry

> Maps role keys to canonical agents and tracks effective-vs-pending dispatch wiring.

## Overview

A **role** is a stable key that identifies a class of subagent dispatch (e.g., `q_gate_validation`, `pr_creation`, `research`). Users configure model levels by role (`models.roles.<role> = <level>`); dispatch sites use the role key at runtime to look up the level and compute the variant agent name. This decouples user configuration from agent file naming — renaming an agent requires updating only the registry row, not every user's `marshal.json`.

The registry below is the single source of truth for which roles exist and which canonical agent each role binds to. Adding a new role requires:

1. A row in this registry.
2. The canonical agent declares `implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor` (see [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md)).
3. Dispatch sites read the role via `manage-config models read --role <name>`.

## Status Legend

| Status | Meaning |
|--------|---------|
| **effective** | Dispatch sites consume this role today. Setting `models.roles.<role>` has runtime effect. |
| **pending** | Schema validates the role (it can be configured), but no dispatch site reads it yet. Configuration is preserved across saves but produces no runtime effect until wrapping work lands. |

The wizard (`marshall-steward` Models submenu) surfaces both effective and pending roles, flagging pending rows so users know configuration is preserved but not active.

## Registry

| Role Key | Canonical Agent | Bundle | Status | Notes |
|----------|-----------------|--------|--------|-------|
| `q_gate_validation` | `q-gate-validation-agent.md` | plan-marshall | effective | Dispatched by phase-2-refine, phase-3-outline, phase-4-plan q-gate steps. |
| `research` | `research-best-practices-agent.md` | plan-marshall | effective | Dispatched by `dev-general-practices` research step. Recommended level: `high` or `xxhigh`. |
| `pr_creation` | `create-pr-agent.md` | plan-marshall | effective | Dispatched by phase-6-finalize Step 3. |
| `automated_review` | `automated-review-agent.md` | plan-marshall | effective | Dispatched by phase-6-finalize Step 3. |
| `sonar_roundtrip` | `sonar-roundtrip-agent.md` | plan-marshall | effective | Dispatched by phase-6-finalize Step 3. |
| `lessons_capture` | `lessons-capture-agent.md` | plan-marshall | effective | Dispatched by phase-6-finalize Step 3. |
| `change_type_detection` | `detect-change-type-agent.md` | plan-marshall | effective | Dispatched by phase-3-outline change-type detection. |
| `phase_init` | `phase-agent.md` | plan-marshall | effective | Phase-agent dispatched for phase-1-init by `plan-marshall/workflows/planning.md` and `recipe.md`. |
| `phase_plan` | `phase-agent.md` | plan-marshall | effective | Phase-agent dispatched for phase-4-plan by `planning.md`. |
| `component_analysis` | `ext-outline-component-agent.md` | pm-plugin-development | effective | Variant infrastructure in place; activation in real workflows is deferred (no current dispatch site, but schema is wired). |
| `inventory_analysis` | `ext-outline-inventory-agent.md` | pm-plugin-development | effective | Same as `component_analysis`. |
| `tool_coverage_analysis` | `tool-coverage-agent.md` | pm-plugin-development | effective | Dispatched by `plugin-doctor/standards/doctor-marketplace.md`. |
| `phase_refine` | `phase-agent.md` | plan-marshall | pending | Phase-2-refine phase-agent dispatch site does not yet read role. |
| `phase_outline` | `phase-agent.md` | plan-marshall | pending | Phase-3-outline phase-agent dispatch site does not yet read role. |
| `phase_execute` | `phase-agent.md` | plan-marshall | pending | Phase-5-execute phase-agent dispatch site does not yet read role. |
| `phase_finalize` | `phase-agent.md` | plan-marshall | pending | Phase-6-finalize phase-agent dispatch site does not yet read role. |
| `retrospective` | (not yet bound) | plan-marshall | pending | Reserved for `plan-retrospective` skill when it grows a subagent dispatch. |
| `implementation` | (not yet bound) | plan-marshall | pending | Reserved for the per-task implementation dispatcher in `execute-task` when it grows agent-level dispatch. |
| `testing` | (not yet bound) | plan-marshall | pending | Reserved for the per-task module-testing dispatcher in `execute-task`. |
| `build_runner` | (not yet bound) | plan-marshall | pending | Reserved for build-system subagents (none today). |

### Per-Phase Roles Share Phase-Agent

`phase_init`, `phase_plan`, `phase_refine`, `phase_outline`, `phase_execute`, `phase_finalize` all map to the same canonical agent file (`phase-agent.md`). The build target emits a single set of variants for `phase-agent`; the role keys differentiate **dispatch context** (which phase is being entered), not agent identity. Configuring `models.roles.phase_init = "high"` and `models.roles.phase_plan = "low"` causes the same canonical to be dispatched as different variants per phase — the variant suffix is computed from the role's resolved level, not from the agent name.

## Cross-References

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Agent-level extension point — declares an agent participates in variant emission. |
| [`model-levels.md`](model-levels.md) | Level → `(model, effort)` primitive binding. |
| [`role-variants.md`](role-variants.md) | User-facing centralised doc for configuring roles. |
| `marshall-steward/standards/models-menu.md` | Wizard UX for editing the `models` block. |

## Adding a New Role

1. Add a row to the **Registry** table above with `pending` status if no dispatch site exists yet.
2. Ensure the canonical agent file declares `implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor` (deliverable 7 of the variant-emission plan).
3. When the first dispatch site is written, flip the row to `effective` and patch the dispatch site per `role-variants.md` § Dispatch Pattern.
4. Run `/marshall-steward` to regenerate any cached registry data.
