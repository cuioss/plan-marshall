# Effort Roles — Role Registry

> Hierarchical role-key registry that maps role keys to LLM-judgement workflows. Users configure effort levels by role key (`plan.<phase>.effort[.<subkey>] = <level>`); dispatch sites use the role key at runtime to look up the level and compute the `execution-context-{level}` variant target.

## Overview

A **role** is a stable key that identifies a class of subagent dispatch (e.g., `phase-1-init`, `phase-6-finalize.verification-feedback`). The role key sits at the LLM-judgement-workflow layer, NOT at the manifest-step / call-site layer — multiple call sites that dispatch the same LLM-judgement workflow from the same phase share one role key.

The registry is **phase-scoped**: every role key sits under a `phase-N-{suffix}` group whose name matches the SKILL.md it identifies (`phase-1-init`, `phase-2-refine`, `phase-3-outline`, `phase-4-plan`, `phase-5-execute`, `phase-6-finalize`). Workflows that fire from multiple phases inherit the calling phase's level via bubbling resolution (`plan.<phase>.effort.<subkey>` → `plan.<phase>.effort.default` → `plan.effort` → `inherit`). The calling phase is supplied by the dispatch site via `--phase phase-N-{suffix}`.

Research dispatches do NOT get their own sub-key — they inherit the calling phase's default (or use `--default` for standalone `/research` outside any plan).

## Storage layout

Per-phase effort config lives **inside the matching `plan.<phase>` entry** under the `effort` key — co-located with the rest of the phase's knobs (steps, max_iterations, etc.). The `plan.effort` field is the plan-wide fallback (a single string):

```jsonc
{
  "plan": {
    "effort": "<level>",                                                       // plan-wide fallback (single string)
    "phase-1-init":     { /* other knobs */, "effort": "<level>" },           // string OR { default? }
    "phase-2-refine":   { /* other knobs */, "effort": "<level>" },           // string OR { default? }
    "phase-3-outline":  { /* other knobs */, "effort": "<level>" },           // string OR { default? }
    "phase-4-plan":     { /* other knobs */, "effort": "<level>" },           // string OR { default? }
    "phase-5-execute":  { /* other knobs */, "effort": "<level>" },           // string OR { default?, verification-feedback? }
    "phase-6-finalize": {                                                      // typically object
      /* other knobs */,
      "effort": {
        "default":                "<level>",   // applies to every phase-6-finalize workflow without its own sub-key
        "verification-feedback":  "<level>",   // override for the unified feedback role
        "post-run-review":        "<level>"    // override for retrospective + lessons-capture
      }
    }
  }
}
```

Total: **6 top-level role groups**. Every group is polymorphic — its `effort` value may be a string (single-level shorthand for the entire phase) or an object whose sub-keys are listed below. **Zero mandatory keys**: a minimal config is `{}` and every dispatch resolves via `plan.effort` → `inherit`.

## Groups

| Group | SKILL it matches | Workflow shape |
|-------|------------------|----------------|
| `phase-1-init` | `plan-marshall:phase-1-init` | Single primary workflow (init body). Dispatched on phase-1-init entry by the planning workflow. |
| `phase-2-refine` | `plan-marshall:phase-2-refine` | Single primary workflow (refine-analyze; confidence loop bundled). Dispatched on phase-2-refine entry. |
| `phase-3-outline` | `plan-marshall:phase-3-outline` | Single primary workflow (outline; `track={simple|complex}` is a runtime input). Dispatched on phase-3-outline entry. |
| `phase-4-plan` | `plan-marshall:phase-4-plan` | Single primary workflow (plan-all-tasks; Steps 5+6+7 bundled). Dispatched on phase-4-plan entry. |
| `phase-5-execute` | `plan-marshall:phase-5-execute` | Per-task execute body, plus `verification-feedback` for build-runner / quality-gate triage. |
| `phase-6-finalize` | `plan-marshall:phase-6-finalize` | Several workflows with distinct cost profiles — finalize body + verification-feedback (sonar / pr-comment / plugin-doctor / pr-state) + post-run-review (retrospective + lessons-capture). |

## Per-phase sub-keys

| Group | Sub-keys |
|-------|----------|
| `phase-1-init`     | `default` |
| `phase-2-refine`   | `default` |
| `phase-3-outline`  | `default` |
| `phase-4-plan`     | `default` |
| `phase-5-execute`  | `default`, `verification-feedback` |
| `phase-6-finalize` | `default`, `verification-feedback`, `post-run-review` |

| Sub-key | LLM-judgement workflow | Where it fires |
|---------|------------------------|----------------|
| `default` | The phase's primary workflow body (or any sub-workflow without its own sub-key — see "Workflow → resolver-key mapping" below). Also covers research dispatched from inside the phase, q-gate-validation, manage-architecture-enrich-module, create-pr, pre-submission-self-review, etc. | Every dispatch under that phase that does NOT pass `--role <subkey>`. |
| `verification-feedback` | Per-finding FIX / SUPPRESS / ACCEPT / AskUserQuestion triage with smart grouping. Producer-mode runtime input branches the data source: `build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`. | phase-5-execute Step 11 + Step 11b (producer=build-runner); phase-6-finalize sonar-roundtrip (sonar), automated-review (pr-comment), `project:finalize-step-plugin-doctor` (plugin-doctor), `/workflow-pr-doctor` slash command (pr-state). |
| `post-run-review` | Retrospective (eight LLM aspects) plus lessons extraction — both look back at the full plan history and ride the same level. | Opt-in `default:retrospective` / `default:lessons-capture` finalize steps AND the user-invokable `/plan-retrospective` slash command. |

## Workflow → resolver-key mapping

Every dispatch site computes the level via `manage-config effort read --phase <caller-phase> [--role <workflow>]`. Workflows without an explicit sub-key resolve via the phase's `default` slot (or the bare phase string).

| LLM workflow | Caller phase | Resolver lookup |
|--------------|--------------|-----------------|
| phase-1-init body | phase-1-init | `plan.phase-1-init.effort.default` → `plan.phase-1-init.effort` (string) → `plan.effort` |
| phase-2-refine body | phase-2-refine | `plan.phase-2-refine.effort.default` → `plan.phase-2-refine.effort` → `plan.effort` |
| phase-3-outline body | phase-3-outline | `plan.phase-3-outline.effort.default` → `plan.phase-3-outline.effort` → `plan.effort` |
| phase-4-plan body | phase-4-plan | `plan.phase-4-plan.effort.default` → `plan.phase-4-plan.effort` → `plan.effort` |
| phase-5-execute task body | phase-5-execute | `plan.phase-5-execute.effort.default` → `plan.phase-5-execute.effort` → `plan.effort` |
| q-gate-validation | phase-2-refine / phase-3-outline / phase-4-plan | calling phase's `default` *(no sub-key)* |
| manage-architecture-enrich-module | phase-6-finalize | `plan.phase-6-finalize.effort.default` *(no sub-key)* |
| create-pr | phase-6-finalize | `plan.phase-6-finalize.effort.default` *(no sub-key)* |
| pre-submission-self-review | phase-6-finalize | `plan.phase-6-finalize.effort.default` *(no sub-key)* |
| research (in-phase) | any phase | calling phase's `default` *(no sub-key)* |
| research (`/research` standalone) | none | `--default` (zero-role fallback) |
| verification-feedback (`producer=build-runner`) | phase-5-execute | `plan.phase-5-execute.effort.verification-feedback` → `plan.phase-5-execute.effort.default` → `plan.effort` |
| verification-feedback (`producer=sonar` / `pr-comment` / `plugin-doctor` / `pr-state`) | phase-6-finalize | `plan.phase-6-finalize.effort.verification-feedback` → `plan.phase-6-finalize.effort.default` → `plan.effort` |
| post-run-review (retrospective + lessons-capture) | phase-6-finalize | `plan.phase-6-finalize.effort.post-run-review` → `plan.phase-6-finalize.effort.default` → `plan.effort` |
| `/workflow-pr-doctor`, `/plugin-doctor`, `/plan-retrospective` slash commands | phase-6-finalize (synthetic) | The slash command body resolves via `--phase phase-6-finalize --role <matching sub-key>` so the same phase-6-finalize configuration applies whether the workflow fires from finalize or from the slash command. |

## Resolver

`manage-config effort read` accepts four lookup forms:

```bash
# Bare group via --role (resolves through <group>.default, then `plan.effort`, then inherit)
manage-config effort read --role phase-2-refine

# Dotted form
manage-config effort read --role phase-6-finalize.verification-feedback

# Two-flag form
manage-config effort read --phase phase-6-finalize --role verification-feedback

# Bare group via --phase (equivalent to bare --role)
manage-config effort read --phase phase-6-finalize
```

For free-standing fallback dispatches (no role key applies — typically the LLM-fallback branch of a hybrid script, or the `/research` slash command outside any plan), the `--default` flag returns the `plan.effort` directly without a role lookup:

```bash
manage-config effort read --default
```

To collapse the per-dispatch-site recipe `level = …; target = canonical if level=="inherit" else canonical-{level}` into one call, the `resolve-target` subcommand returns the variant target name directly:

```bash
manage-config effort resolve-target --phase phase-6-finalize --role verification-feedback
# → target: execution-context-high (or "execution-context" when level == inherit)
```

### Resolution order

1. **Sub-key in the registry?** The supplied `subkey` must appear in the group's schema (see "Per-phase sub-keys" above) — unknown sub-keys error.
2. **`plan.<group>.effort` walked per the polymorphic-value rule**:
   - **String** at the phase entry → the value is the level. Any sub-key lookup on a string-valued effort resolves to the same value (single-level shorthand).
   - **Object** at the phase entry → sub-key supplied AND present → that value. Sub-key supplied but absent → walk to the `default` slot. Sub-key absent (bare-group lookup) → walk to the `default` slot.
3. **Top-level `effort`** → fall through when the phase is absent OR the object lacks both the sub-key and the `default` slot.
4. **`inherit`** → implicit final fallback when neither the per-phase `effort` nor the `plan.effort` is configured.

The resolver validates the resolved value against `ALLOWED_LEVELS` from `effort-levels.md`. Unknown role groups (typos, stale references) resolve to the `plan.effort` fallback with a non-fatal warning so a single misspelled key cannot wedge the whole dispatch flow.

### Sub-dispatch from inside a subagent envelope

Some dispatch sites fire from *inside* a running subagent envelope (not from the orchestrator's main context) — for example, a phase-N subagent kicking off `research` mid-flow, or the `verification-feedback` envelope sub-dispatching itself on overflow. The sub-dispatch must resolve the level via the **caller's** phase, not via `--default`.

The mechanism: the dispatch prompt body's existing `name` field encodes the caller phase **directly** — the prompt-body `name:` value matches the registry key one-for-one (e.g. `name: phase-2-refine` → caller phase IS `phase-2-refine`). For workflows whose `name:` does not naturally encode the phase (a workflow shared across phases such as `verification-feedback` or `q-gate-validation`), the parent's prompt body passes an explicit `caller_phase` field — a 6th-field optional extension of the canonical 5-field contract. See `extension-api/standards/ext-point-execution-context-workflow.md` § Sub-dispatch contract for the full propagation rule.

## Cross-references

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Agent-side ext-point — declares the dispatcher agent participates in variant emission. |
| [`ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) | Workflow-doc ext-point — declares a workflow doc is dispatchable by `execution-context`. Sub-dispatch contract documented here. |
| [`effort-levels.md`](effort-levels.md) | Level → `(model, effort)` primitive binding. |
| [`effort-variants.md`](effort-variants.md) | User-facing centralised doc for configuring effort. |
| `marshall-steward/standards/effort-menu.md` | Wizard UX for editing the per-phase effort attributes. |
| [`marketplace/bundles/plan-marshall/scripts/effort_presets.py`](../scripts/effort_presets.py) | Preset payloads — `ECONOMIC`, `BALANCED`, `HIGH_END` — written by `manage-config effort apply-preset`. Re-anchored on a 3-tier monotonic ladder (`economic` ≤ `balanced` ≤ `high-end` on every phase/role); `BALANCED` is stored in literal-expanded form to mirror the on-disk shape `apply-preset` writes (so the wizard's deep-equality match recognises it after apply). |

## Adding a new role

1. Decide the right phase. A workflow with no natural phase home (because it genuinely fires from many phases) does NOT get a top-level group — it gets a sub-key under whichever phase invokes it, and the caller passes `--phase phase-N-{suffix}` at dispatch time.
2. Confirm the workflow earns its dispatch envelope per the granularity heuristics (script-only or trivial-inline work does NOT get a role key).
3. Add the new sub-key to the appropriate row of "Per-phase sub-keys" above (and to the JSON sample at the top of this file).
4. Update `_cmd_effort.py`'s `KNOWN_ROLES` tuple for the affected group.
5. Update `effort_presets.py` if any preset should set a non-default effort for the new sub-key.
6. Wire the dispatch site through `manage-config effort resolve-target --phase phase-N-{suffix} --role <subkey>` and pass `name` + `plan_id` + `skills[]` + `workflow` + `WORKTREE` via the prompt body.
