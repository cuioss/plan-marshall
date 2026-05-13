# Model Roles — Role Registry

> Hierarchical role-key registry that maps role keys to LLM-judgement workflows. Users configure model levels by role key (`models.roles.<phase>[.<subkey>] = <level>`); dispatch sites use the role key at runtime to look up the level and compute the `execution-context-{level}` variant target.

## Overview

A **role** is a stable key that identifies a class of subagent dispatch (e.g., `phase-1`, `phase-6.verification-feedback`, `phase-3.research`). The role key sits at the LLM-judgement-workflow layer, NOT at the manifest-step / call-site layer — multiple call sites that dispatch the same LLM-judgement workflow from the same phase share one role key.

The registry is **phase-scoped**: every role key sits under a `phase-N` group. There is no `cross.*` group; workflows that fire from multiple phases inherit the calling phase's level via bubbling resolution (`phase-N.<subkey>` → `phase-N.default` → `models.default` → `inherit`). The calling phase is supplied by the dispatch site via `--phase phase-N`.

## Registry

```jsonc
{
  "models": {
    "default": "medium",
    "roles": {
      "phase-1": "<level>",                   // string OR { default?, research? }
      "phase-2": "<level>",                   // string OR { default?, research? }
      "phase-3": "<level>",                   // string OR { default?, research? }
      "phase-4": "<level>",                   // string OR { default?, research? }
      "phase-5": "<level>",                   // string OR { default?, verification-feedback?, research? }
      "phase-6": {                            // typically object
        "default":                "<level>",  // applies to every phase-6 workflow without its own sub-key
        "verification-feedback":  "<level>",  // override for the unified feedback role
        "post-run-review":        "<level>",  // override for retrospective + lessons-capture
        "research":               "<level>"   // override for external research dispatched from phase-6
      }
    }
  }
}
```

Total: **6 top-level role groups**. Every group is polymorphic — its value may be a string (single-level shorthand for the entire phase) or an object whose sub-keys are listed below. **Zero mandatory keys**: a minimal config is `{}` and every dispatch resolves via `models.default` → `inherit`.

## Groups

| Group | Workflow shape | Resolved by |
|-------|----------------|-------------|
| `phase-1` | Single primary workflow (phase-1-init body) plus optional in-phase research | Dispatched on phase-1 entry by the planning workflow |
| `phase-2` | Single primary workflow (refine-analyze) plus optional in-phase research | Dispatched on phase-2 entry |
| `phase-3` | Single primary workflow (outline; `track=simple|complex` is a runtime input) plus optional research | Dispatched on phase-3 entry |
| `phase-4` | Single primary workflow (plan-all-tasks; Steps 5+6+7 bundled) plus optional research | Dispatched on phase-4 entry |
| `phase-5` | Per-task execute body, plus `verification-feedback` for build-runner / quality-gate triage, plus optional research | Per-task dispatcher inside phase-5-execute |
| `phase-6` | Several workflows with distinct cost profiles — finalize body + verification-feedback (sonar / pr-comment / plugin-doctor / pr-state) + post-run-review (retrospective + lessons-capture) + research | Each sub-key (or the unspecified `default`) is dispatched at a different point in the finalize loop |

## Per-phase sub-keys

| Group | Sub-keys |
|-------|----------|
| `phase-1` | `default`, `research` |
| `phase-2` | `default`, `research` |
| `phase-3` | `default`, `research` |
| `phase-4` | `default`, `research` |
| `phase-5` | `default`, `verification-feedback`, `research` |
| `phase-6` | `default`, `verification-feedback`, `post-run-review`, `research` |

| Sub-key | LLM-judgement workflow | Where it fires |
|---------|------------------------|----------------|
| `default` | The phase's primary workflow body (or any sub-workflow without its own sub-key — see "Workflow → resolver-key mapping" below). | Every dispatch under that phase that does NOT pass `--role <subkey>`. |
| `research` | Comprehensive web-based research with confidence scoring against 10+ sources. | `dev-general-practices`-loaded contexts inside any phase that needs external research; resolves under the caller phase's group. |
| `verification-feedback` | Per-finding FIX / SUPPRESS / ACCEPT / AskUserQuestion triage with smart grouping (pre-group by `(domain, rule_id)`, one batched LLM decision per group). Producer-mode runtime input branches the data source: `build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`. | phase-5 Step 11 + Step 11b (producer=build-runner); phase-6 sonar-roundtrip (sonar), automated-review (pr-comment), `project:finalize-step-plugin-doctor` (plugin-doctor), `/pr-doctor` slash command (pr-state). |
| `post-run-review` | Retrospective (eight LLM aspects: premise, scope, ambiguity, evidence, plan hygiene, execution discipline, integration, decision log) plus lessons extraction — both look back at the full plan history and ride the same level. | Opt-in `default:retrospective` / `default:lessons-capture` finalize steps AND the user-invokable `/plan-retrospective` slash command. |

## Workflow → resolver-key mapping

Every dispatch site computes the level via `manage-config models read --phase <caller-phase> [--role <workflow>]`. Workflows without an explicit sub-key resolve via the phase's `default` slot (or the bare phase string).

| LLM workflow | Caller phase | Resolver lookup |
|--------------|--------------|-----------------|
| phase-1 body | phase-1 | `phase-1.default` → `phase-1` (string) → `default` |
| phase-2 body | phase-2 | `phase-2.default` → `phase-2` → `default` |
| phase-3 body | phase-3 | `phase-3.default` → `phase-3` → `default` |
| phase-4 body | phase-4 | `phase-4.default` → `phase-4` → `default` |
| phase-5 task body | phase-5 | `phase-5.default` → `phase-5` → `default` |
| q-gate-validation | phase-2 / phase-3 / phase-4 | `phase-N.default` → `phase-N` → `default` *(no sub-key)* |
| manage-architecture-enrich-module | phase-6 | `phase-6.default` → `default` *(no sub-key)* |
| create-pr | phase-6 | `phase-6.default` → `default` *(no sub-key)* |
| pre-submission-self-review | phase-6 | `phase-6.default` → `default` *(no sub-key)* |
| research | any phase N | `phase-N.research` → `phase-N.default` → `phase-N` → `default` |
| verification-feedback (`producer=build-runner`) | phase-5 | `phase-5.verification-feedback` → `phase-5.default` → `phase-5` → `default` |
| verification-feedback (`producer=sonar` / `pr-comment` / `plugin-doctor` / `pr-state`) | phase-6 | `phase-6.verification-feedback` → `phase-6.default` → `default` |
| post-run-review (retrospective + lessons-capture) | phase-6 | `phase-6.post-run-review` → `phase-6.default` → `default` |
| `/pr-doctor`, `/plugin-doctor`, `/plan-retrospective` slash commands | `phase-6` (synthetic) | The slash command body resolves via `--phase phase-6 --role <matching sub-key>` so the same phase-6 configuration applies whether the workflow fires from finalize or from the slash command. |
| `/research` slash command outside any plan | none | `manage-config models read --default` (zero-role fallback) |

## Resolver

`manage-config models read` accepts four lookup forms:

```bash
# Bare group via --role (resolves through <group>.default, then models.default, then inherit)
manage-config models read --role phase-2

# Dotted form
manage-config models read --role phase-6.verification-feedback

# Two-flag form
manage-config models read --phase phase-6 --role verification-feedback

# Bare group via --phase (equivalent to bare --role)
manage-config models read --phase phase-6
```

For free-standing fallback dispatches (no role key applies — typically the LLM-fallback branch of a hybrid script, or the `/research` slash command outside any plan), the `--default` flag returns `models.default` directly without a role lookup:

```bash
manage-config models read --default
```

To collapse the per-dispatch-site recipe `level = …; target = canonical if level=="inherit" else canonical-{level}` into one call, the `resolve-target` subcommand returns the variant target name directly:

```bash
manage-config models resolve-target --phase phase-6 --role verification-feedback
# → target: execution-context-high (or "execution-context" when level == inherit)
```

### Resolution order

1. **Sub-key in the registry?** The supplied `subkey` must appear in the group's schema (see "Per-phase sub-keys" above) — unknown sub-keys error. Retired legacy keys (`cross.*`, `phase-6.{create-pr,pre-submission-self-review,lessons-capture,retrospective,pr-doctor}`) error with a remediation message.
2. **`models.roles.<group>` walked per the polymorphic-value rule**:
   - **String** at group → the value is the level. Any sub-key lookup on a string-valued group resolves to the same value (single-level shorthand).
   - **Object** at group → sub-key supplied AND present → that value. Sub-key supplied but absent → walk to the `default` slot. Sub-key absent (bare-group lookup) → walk to the `default` slot.
3. **`models.default`** → fall through when the group is absent OR the object lacks both the sub-key and the `default` slot.
4. **`inherit`** → implicit final fallback when neither group nor `models.default` is configured.

The resolver validates the resolved value against `ALLOWED_LEVELS` from `model-levels.md` and emits a warning (not an error) when the requested role group is not registered in this document — registry renames must not break saved configs.

### Sub-dispatch from inside a subagent envelope

Some dispatch sites fire from *inside* a running subagent envelope (not from the orchestrator's main context) — for example, a phase-N subagent kicking off `research` mid-flow, or the `verification-feedback` envelope sub-dispatching `triage` overflow. The sub-dispatch must resolve the level via the **caller's** phase, not via `--default`.

The mechanism: the dispatch prompt body's existing `name` field encodes the caller phase implicitly (`name: phase-2-refine` → caller phase is `phase-2`). For workflows that don't naturally encode the phase in their name, the parent's prompt body passes an explicit `caller_phase` field — a 6th-field optional extension of the canonical 5-field contract. See `extension-api/standards/ext-point-execution-context-workflow.md` § Sub-dispatch contract for the full propagation rule.

## Cross-references

| Document | Content |
|----------|---------|
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Agent-side ext-point — declares the dispatcher agent participates in variant emission. |
| [`ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) | Workflow-doc ext-point — declares a workflow doc is dispatchable by `execution-context`. Sub-dispatch contract documented here. |
| [`model-levels.md`](model-levels.md) | Level → `(model, effort)` primitive binding. |
| [`role-variants.md`](role-variants.md) | User-facing centralised doc for configuring roles. |
| `marshall-steward/standards/models-menu.md` | Wizard UX for editing the `models` block. |
| [`marketplace/bundles/plan-marshall/scripts/model_presets.py`](../scripts/model_presets.py) | Preset payloads — `ECONOMIC`, `BALANCED`, `HIGH_END` — written by `manage-config models apply-preset`. |

## Adding a new role

1. Decide the right phase. A workflow with no natural phase home (because it genuinely fires from many phases) does NOT get a top-level group — it gets a sub-key under whichever phase invokes it, and the caller passes `--phase phase-N` at dispatch time.
2. Confirm the workflow earns its dispatch envelope per the granularity heuristics (script-only or trivial-inline work does NOT get a role key).
3. Add the new sub-key to the appropriate row of "Per-phase sub-keys" above (and to the JSON sample at the top of this file).
4. Update `_cmd_models.py`'s `KNOWN_ROLES` tuple for the affected group.
5. Update `model_presets.py` if any preset should set a non-default level for the new sub-key.
6. Wire the dispatch site through `manage-config models resolve-target --phase phase-N --role <subkey>` and pass `name` + `plan_id` + `skills[]` + `workflow` + `WORKTREE` via the prompt body.
