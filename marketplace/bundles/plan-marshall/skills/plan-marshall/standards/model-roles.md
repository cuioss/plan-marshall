# Model Roles — Role Registry

> Hierarchical role-key registry that maps role keys to LLM-judgement workflows. Users configure model levels by role key (`models.roles.<group>[.<subkey>] = <level>`); dispatch sites use the role key at runtime to look up the level and compute the `execution-context-{level}` variant target.

## Overview

A **role** is a stable key that identifies a class of subagent dispatch (e.g., `phase-1`, `phase-6.create-pr`, `cross.triage`). The role key sits at the LLM-judgement-workflow layer, NOT at the manifest-step / call-site layer — multiple call sites that dispatch the same LLM-judgement workflow share one role key (see `cross.triage`).

The registry is **two levels deep**: a top-level group (the seven groups below) and, when the group spans multiple workflows, a kebab-case subkey identifying the specific workflow. Single-workflow groups (`phase-1` through `phase-5`) carry a flat string value; multi-workflow groups (`phase-6`, `cross`) carry a nested object keyed by subkey.

## Registry

```json
{
  "models": {
    "default": "medium",
    "roles": {
      "phase-1": "<level>",
      "phase-2": "<level>",
      "phase-3": "<level>",
      "phase-4": "<level>",
      "phase-5": "<level>",
      "phase-6": {
        "pre-submission-self-review": "<level>",
        "create-pr": "<level>",
        "lessons-capture": "<level>",
        "retrospective": "<level>",
        "pr-doctor": "<level>"
      },
      "cross": {
        "research": "<level>",
        "triage": "<level>",
        "q-gate-validation": "<level>",
        "plugin-doctor": "<level>",
        "manage-architecture-enrich-module": "<level>"
      }
    }
  }
}
```

Total: **15 role keys across 7 groups**.

## Groups

| Group | Workflow shape | Resolved by |
|-------|----------------|-------------|
| `phase-1` | Flat string — single workflow (phase-1-init body) | Dispatched on phase-1 entry by the planning workflow |
| `phase-2` | Flat string — single workflow (refine-analyze; confidence loop bundled) | Dispatched on phase-2 entry |
| `phase-3` | Flat string — single workflow (outline; `track=simple|complex` is a runtime input) | Dispatched on phase-3 entry |
| `phase-4` | Flat string — single workflow (plan-all-tasks; Steps 5+6+7 bundled) | Dispatched on phase-4 entry |
| `phase-5` | Flat string — single workflow (task-execute; dispatched once per task in the queue) | Per-task dispatcher inside phase-5-execute |
| `phase-6` | Nested object — five distinct LLM-judgement workflows with different cost profiles | Each subkey is dispatched at a different point in the finalize loop |
| `cross` | Nested object — five workflows that fire from multiple phases or outside the plan workflow entirely | Dispatched from the call sites listed per-subkey below |

## phase-6 subkeys

| Subkey | LLM-judgement workflow | Call site(s) |
|--------|------------------------|--------------|
| `pre-submission-self-review` | Structural review (symmetric pairs, regex over-fit, user-facing strings, markdown sections, contract drift) against the deterministic candidate-surface output of `tools-self-review:self_review`. | `project:finalize-step-pre-submission-self-review` (meta-project only; consumer projects do not register this step) |
| `create-pr` | PR title / body / labels composition from plan context (request, solution outline, deliverables, decision log). | `default:create-pr` manifest step |
| `lessons-capture` | Lesson extraction + per-lesson body composition from the plan's history; persistence scripts wrap the dispatch. | `default:lessons-capture` manifest step |
| `retrospective` | Eight LLM aspects (premise, scope, ambiguity, evidence, plan hygiene, execution discipline, integration, decision log) iterated inside one dispatch envelope. | Opt-in `default:retrospective` finalize step AND the user-invokable `/plan-retrospective` slash command — both operate on phase-6 plan-completion artefacts |
| `pr-doctor` | Diagnose + report + per-finding internal triage iteration. Internal iteration may sub-dispatch `cross.triage` or iterate in-context inside pr-doctor's envelope. | Opt-in `default:pr-doctor` finalize step AND the user-invokable `/pr-doctor` slash command |

## cross subkeys

| Subkey | LLM-judgement workflow | Call site(s) |
|--------|------------------------|--------------|
| `research` | Comprehensive web-based research with confidence scoring against 10+ sources. | `dev-general-practices`-loaded contexts in any phase that needs external research |
| `triage` | Per-finding FIX / SUPPRESS / ACCEPT / AskUserQuestion decisions with smart grouping (pre-group by `(domain, rule_id)`, one batched LLM decision per group, sequential actions between groups). | phase-5-execute Step 11 (`verification-failure`), Step 11b (`quality-gate-failure`), phase-6 `automated-review` (`pr-comment`), phase-6 `sonar-roundtrip` (`sonar-issue`), `workflow-pr-doctor` internal loop |
| `q-gate-validation` | Validate solution-outline deliverables against request intent and per-file assessments — catch false positives, missing coverage, scope drift. | phase-3-outline Complex Track Step 11 AND phase-4-plan Step 9b (each call site activates a different validator subset via runtime `activation_context`/`validators` parameters) |
| `plugin-doctor` | Plugin / agent / command / skill diagnostics with `scope` as a runtime input (`agents`, `commands`, `skills`, `scripts`, `metadata`, `skill-content`, `skill-knowledge`, `test-conventions`, `marketplace`, `plan-marshall`). | Developer tool outside any plan AND `project:finalize-step-plugin-doctor` in the plan-marshall meta-project |
| `manage-architecture-enrich-module` | Per-module enrichment of architecture descriptors (responsibility, key_packages, summary). The only per-iteration **parallel** dispatch in the contract — one dispatch per affected module, all in parallel. | `default:architecture-refresh` Tier-1 in phase-6-finalize |

## Resolver

`manage-config models read --role <key>` accepts three lookup forms:

```bash
# Bare-group lookup — only legal for flat groups (phase-1…phase-5)
manage-config models read --role phase-2

# Dotted form — required for nested groups
manage-config models read --role phase-6.create-pr
manage-config models read --role cross.triage

# Two-flag form — equivalent to dotted, convenient when iterating within a group
manage-config models read --phase phase-6 --role create-pr
```

For free-standing fallback dispatches (no role key applies — typically the LLM-fallback branch of a hybrid script), the `--default` flag returns `models.default` directly without a role lookup:

```bash
manage-config models read --default
```

To collapse the per-dispatch-site recipe `level = …; target = canonical if level=="inherit" else canonical-{level}` into one call, the `resolve-target` subcommand returns the variant target name directly:

```bash
manage-config models resolve-target --role cross.triage
# → target: execution-context-high (or "execution-context" when level == inherit)
```

### Resolution order

1. `models.roles.<group>` walked per the polymorphic-value rule:
   - **String** at group → the value is the level. Any sub-key lookup on a flat group resolves to the same value.
   - **Object** at group → walk to `[subkey]`. Bare-group lookup on a multi-workflow group is an error (sub-key required).
2. `models.default` → fall through when the role/subkey is unset.
3. `inherit` → implicit final fallback when neither role nor default is configured.

The resolver validates the resolved value against `ALLOWED_LEVELS` from `model-levels.md` and emits a warning (not an error) when the requested role group is not registered in this document — registry renames must not break saved configs.

## Cross-references

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Agent-side ext-point — declares the dispatcher agent participates in variant emission. |
| [`ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) | Workflow-doc ext-point — declares a workflow doc is dispatchable by `execution-context`. |
| [`model-levels.md`](model-levels.md) | Level → `(model, effort)` primitive binding. |
| [`role-variants.md`](role-variants.md) | User-facing centralised doc for configuring roles. |
| `marshall-steward/standards/models-menu.md` | Wizard UX for editing the `models` block. |
| [`marketplace/bundles/plan-marshall/scripts/model_presets.py`](../scripts/model_presets.py) | Preset payloads — `ECONOMIC`, `BALANCED`, `HIGH_END` — written by `manage-config models apply-preset`. |

## Adding a new role

1. Decide the right group: a workflow goes in `cross` only if it genuinely fires from multiple phases (or outside the plan workflow entirely). Multiple call sites within ONE phase do not promote to `cross` — they remain under that phase's group.
2. Confirm the workflow earns its dispatch envelope per the granularity heuristics (script-only or trivial-inline work does NOT get a role key).
3. Add the new entry to the registry above (and the JSON sample at the top of this file).
4. Update `_cmd_models.py`'s `KNOWN_ROLES` map to register the new group / subkey.
5. Update `model_presets.py` if any preset should set a non-default level for the new role.
6. Wire the dispatch site through `manage-config models resolve-target --role <key>` and pass `name` + `plan_id` + `skills[]` + `workflow` + `WORKTREE` via the prompt body.
