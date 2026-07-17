---
name: manage-execution-manifest
description: Compose, read, and validate the per-plan execution manifest that drives Phase 5 verification and Phase 6 finalize step selection
user-invocable: false
mode: script-executor
scope: plan
---

# Manage Execution Manifest Skill

Compose, read, and validate the per-plan **execution manifest** — a small declarative artifact emitted at the end of `phase-4-plan` that names the exact Phase 5 verification steps and Phase 6 finalize steps for this plan. Phases 5 and 6 become dumb manifest executors; per-doc skip logic in their standards is removed in favor of this single source of truth.

This skill is **script-only**: it has no user-invocable command and is not loaded into LLM context via `Skill:` directives. It is invoked exclusively through the 3-part script notation `plan-marshall:manage-execution-manifest:manage-execution-manifest`. Per the project memory's plugin.json registration rules, it MUST NOT be registered in `plugin.json`.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- The manifest file is the single source of truth for Phase 5/6 step selection — every decision MUST be reflected in the manifest, and every reasoning MUST be logged via `manage-logging decision`.
- The manifest stays lean and diffable. Do not embed reasoning, timestamps, or free-text fields — push those to `decision.log`.
- `compose` is idempotent: re-invocation overwrites the previous manifest. Callers responsible for re-entry semantics.
- The seven-row decision matrix is authoritative. See [decision-rules.md](standards/decision-rules.md) for the canonical table.

## Storage Location

The manifest is stored in the plan directory:

```text
.plan/local/plans/{plan_id}/execution.toon
```

TOON format. Manifest schema:

```toon
manifest_version: 1
plan_id: {plan_id}

phase_5:
  early_terminate: false
  envelope_count: 1
  verification_steps[N]:
    - quality-gate
    - module-tests
    - coverage
  step_execution_tier[N]{step_id,tier}:
    "verify:quality-gate",per_task
    "verify:module-tests",orchestrator
    "verify:coverage",orchestrator

phase_6:
  steps[M]:
    - push
    - create-pr
    - automated-review
    - sonar-roundtrip
    - lessons-capture
    - branch-cleanup
    - archive-plan

execution_log[K]{step_id,phase,outcome,total_tokens,tool_uses,duration_ms,timestamp}:
  - quality_check,5-execute,executed,12000,8,4200,2026-06-08T10:15:00+00:00
  - create-pr,6-finalize,skipped,0,0,0,2026-06-08T10:42:00+00:00
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | int | Schema version (currently `1`) |
| `plan_id` | string | Plan identifier (echo) |
| `phase_5.early_terminate` | bool | If `true`, Phase 5 transitions directly to Phase 6 without running tasks (analysis-only plans with empty affected_files) |
| `phase_5.envelope_count` | int | Number of phase-5 `execution-context` envelopes the orchestrator should plan for. Written by `compose` from the optional `--envelope-count` input; defaults to `1` (a single budget-bounded envelope greedily drives the task loop) when the input is absent. A manifest composed before this field existed has no `phase_5.envelope_count` key, and every reader interprets an absent value as the same `1` default — so reads stay backward-compatible. |
| `phase_5.verification_steps` | list[string] | Ordered list of Phase 5 verification step IDs (e.g., `quality-gate`, `module-tests`, `coverage`). Empty list means no verification needed (e.g., docs-only plans) |
| `phase_5.step_execution_tier` | list[object] | Per-step `execution_tier` record list — one `{step_id, tier}` object per `phase_5.verification_steps` entry, in list order. `tier` is `per_task` (the leaf runs the step inline) or `orchestrator` (the step exceeds the Bash ceiling and is yielded to the orchestrator's `await-long-running` seam). Written by `compose` via `architecture resolve` per step; the list is total over `verification_steps` and every entry carries a resolved tier (unresolved/absent defaults to `per_task`). A record list rather than a keyed map because a step id (`verify:quality-gate`) contains a colon, which does not round-trip as a TOON object key. This is the compose-time structural enforcement of the leaf-no-background-build invariant (see `ref-workflow-architecture/standards/agents.md` § "Leaf cannot reap a backgrounded build"). |
| `phase_6.steps` | list[string] | Ordered list of Phase 6 finalize step IDs to dispatch. Subset of the canonical step set: `push`, `create-pr`, `automated-review`, `sonar-roundtrip`, `lessons-capture`, `adr-propose`, `branch-cleanup`, `archive-plan`, `record-metrics`, `lessons-integration`. CI completion is a dispatcher-resolved precondition declared via `requires: [ci-complete]` on consumer step frontmatters (see `phase-6-finalize/SKILL.md` Step 3 § "Precondition resolution") — it is not itself a step in the canonical set. |
| `phase_5.step_params` | object | Per-step param snapshot for the selected Phase 5 verify steps, keyed by the (bare) in-manifest step id; each value is the step's resolved param object snapshotted from the marshal.json keyed map at compose time. Verify steps own no params, so values are typically `{}`. Read via `step-params get`; per-plan overridable via `step-params set`. |
| `phase_6.step_params` | object | Per-step param snapshot for the selected Phase 6 finalize steps, keyed by the (bare) in-manifest step id; each value is the step's resolved param object snapshotted from the marshal.json keyed map at compose time (e.g. `branch-cleanup` carries `pr_merge_strategy` / `final_merge_without_asking` / `auto_rebase_threshold`; `sonar-roundtrip` carries `touched_file_cleanup` / `do_transition` / `ce_wait_timeout_seconds`; `automated-review` carries `review_bot_buffer_seconds`). This is the **plan-local runtime source** that phase-5/6 consumers read via `step-params get` (per-plan overridable via `step-params set`), NOT the marshal.json keyed map (the compose-time default). |
| `execution_log` | list[object] | Ordered append log of per-step execution records, written one row per `record-step` invocation. Each row carries `step_id` (the dispatched step), `phase` (`5-execute` or `6-finalize`), `outcome` (`executed`/`skipped`/`error`), the token-attribution triple `total_tokens`/`tool_uses`/`duration_ms` (default `0`), and an ISO-8601 `timestamp`. Absent until the first `record-step` call; the `compose`/`read`/`validate`/`validate-loadable` operations never read or write it. |

---

## Operations

Script: `plan-marshall:manage-execution-manifest:manage-execution-manifest`

### compose

Compose and write the execution manifest from inputs gathered at the end of phase-4-plan.

**Step-param snapshot.** In addition to the step lists, `compose` snapshots each SELECTED step's resolved param object — read from the marshal.json keyed map (`plan.phase-{5,6}-{execute,finalize}.{verification_steps,steps}`) — into the manifest body under `phase_5.step_params` / `phase_6.step_params`, keyed by the (bare) in-manifest step id. This is the write-time-snapshot model that already governs the step list: params are baked at compose time exactly like the step list, so the manifest is the plan-local runtime source while marshal.json stays the compose-time default. Only steps that survive selection are snapshotted; a step with no marshal-side param object snapshots as `{}`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  compose \
  --plan-id {plan_id} \
  --change-type {change_type} \
  --track {simple|complex} \
  --scope-estimate {none|surgical|single_module|multi_module|broad} \
  [--recipe-key {recipe_key}] \
  [--affected-files-count {N}] \
  [--phase-5-steps {step1,step2,...}] \
  [--phase-6-steps {step1,step2,...}] \
  [--commit-and-push {true|false}] \
  [--envelope-count {N}] \
  [--aspect {analysis|planning|implementation}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--change-type` (required): `analysis|feature|enhancement|bug_fix|tech_debt|verification`
- `--track` (required): `simple|complex` — outline track from phase-3-outline
- `--scope-estimate` (required): `none|surgical|single_module|multi_module|broad` — from solution outline metadata (deliverable 2)
- `--recipe-key` (optional override): Forces the `recipe` rule. When omitted, the composer reads the provenance itself from `status.json::metadata.plan_source` (falling back to `metadata.recipe_key`), so lesson- and recipe-derived plans select the `recipe` rule without the caller forwarding this flag.
- `--affected-files-count` (optional, default 0): Count of affected files surfaced by the outline; used by the `early_terminate` rule
- `--phase-5-steps` (optional): Comma-separated candidate Phase 5 verification step IDs. The composer prefers `marshal.json::plan.phase-5-execute.verification_steps` (the phase-aware list-field — phase-5 reads `verification_steps`, every other phase reads `steps`; see [decision-rules.md](standards/decision-rules.md) § "Phase-aware step source"), falling back to this CSV only when no marshal.json is present. The IDs may be the legacy bare role-file forms (`default:quality_check`, …) or the parameterized canonical-verify form `default:verify:{canonical}` (e.g. `default:verify:quality-gate`, `default:verify:module-tests`, `default:verify:coverage`), whose matrix role is derived from the trailing canonical segment (see [decision-rules.md](standards/decision-rules.md) § "Role derivation for canonical-verify steps"). The decision matrix selects a subset, then the generic footprint pre-filter (§ "Generic footprint pre-filter") drops any footprint-gated whole-tree canonical (`integration` / `e2e`) that the live footprint does not exercise.
- `--phase-6-steps` (optional): Comma-separated candidate Phase 6 finalize step IDs (e.g., `push,create-pr,automated-review,sonar-roundtrip,lessons-capture,adr-propose,branch-cleanup,archive-plan`). Same fallback-only contract as `--phase-5-steps`: the composer prefers `marshal.json::plan.phase-6-finalize.steps`, consulting this CSV only when no marshal.json is present — so in an inited project the CSV cannot inject a plan-scoped candidate. The decision matrix selects a subset. If both marshal.json and the CSV are absent, defaults to the full canonical set.
- `--commit-and-push` (optional, default `true`): `true|false` — the resolved `commit_and_push` boolean from phase-5-execute config. When `false`, `push`, `pre-push-quality-gate`, and `pre-submission-self-review` are all removed from the candidate set by the `commit_push_disabled` pre-filter before the matrix runs (a local-only run).
- `--envelope-count` (optional, default `1`): Number of phase-5 `execution-context` envelopes the orchestrator should plan for. Persisted into the manifest's `phase_5.envelope_count`. When omitted, defaults to `1` (a single budget-bounded envelope greedily drives the task loop until the queue is empty or a TASK-boundary re-dispatch point fires). A non-positive value is clamped to `1`. The field is written under every decision-matrix rule (including `early_terminate`), so the `phase_5` block always carries it.
- `--aspect` (optional): `analysis|planning|implementation` — the resolved request aspect from the `manage-config aspect-classify` verb (phase-1-init). When `analysis` or `planning`, the **request-aspect step-dropping** pass (§ "Request-aspect step dropping") removes every build / quality-gate / test canonical-verify step (derived roles `quality-gate` / `module-tests` / `coverage`) from the final `phase_5.verification_steps` — an analysis / planning request carries no production / test footprint, so those gates have nothing to gate. When omitted, or `implementation` (the classifier's safe sub-threshold fallback), every build/verify gate is retained. The drop is role-driven and canonical-agnostic; external (`project:` / `bundle:skill`) steps are passed through untouched.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
file: execution.toon
created: true
manifest_version: 1
phase_5:
  early_terminate: false
  verification_steps_count: 2
  envelope_count: 1
  step_execution_tier[2]{step_id,tier}:
    "verify:quality-gate",per_task
    "verify:module-tests",orchestrator
phase_6:
  steps_count: 6
rule_fired: surgical_tech_debt
commit_and_push: true
commit_push_omitted: false
pre_push_quality_gate_omitted: false
pre_submission_self_review_omitted: false
simplify_omitted: true
scope_gated_finalize_dropped[0]:
unresolved_ask_provider_dropped[0]:
drop_review_on_scope_gate: false
ceremony_finalize_gates:
  self_review: auto
  qgate: auto
  simplify: auto
  security_audit: auto
ceremony_finalize_forced_in[0]:
ceremony_finalize_forced_out[0]:
```

#### Compose-time step-resolution gate

As its final gate — after the frontmatter-order sort, over the FINAL emitted `phase_5.verification_steps` and `phase_6.steps` — `compose` resolves every emitted step id and **fails loud** on the first one that does not resolve. This closes the gap left by `validate-loadable`, which only checks built-in standards-file presence and short-circuits every external (`project:` / `bundle:skill`) step to `loadable: true`: a never-existed `bundle:skill` key, a renamed/removed `project:` skill, or a built-in doc deleted without sweeping `marshal.json` would otherwise compose silently and fail only much later at dispatch time.

Resolution is keyed on the step-id shape and the phase:

- **`project:`** step (either phase) resolves iff its project-local `{bare}/SKILL.md` exists under the repo root.
- **phase-5 canonical-verify** step (bare `{canonical}` or `verify:{canonical}`) resolves iff `{canonical}` is in the verify-canonicals universe — the composer's `_CANONICAL_TO_ROLE` keys unioned with every `ext-point-build-verify-step` implementor's declared `canonicals`.
- **phase-5 external `bundle:skill`** verify step resolves iff its (normalized) id is a discovered `ext-point-build-verify-step` implementor name.
- **phase-6 external `bundle:skill`** step resolves iff its (normalized) id is a discovered `ext-point-finalize-step` implementor name (the same `extension_discovery.find_implementors` query the finalize/verify seed and discovery surfaces use — the SOLE discovery path).
- **phase-6 built-in** step (bare / `default:`) keeps the existing standards/workflow file check.

On the first unresolvable id, `compose` returns `status: error`, `error: unresolvable_step`, and a `message` naming the offending **original `marshal.json` key** (mapped back from the boundary-normalized emitted id via `marshal_phase_{5,6}_map`) and the phase — plus `phase`, `step_id`, and `marshal_key` fields — and emits one `decision.log` line. The gate never writes a partial manifest: the error returns before the step-params snapshot and `write_manifest`.

```toon
status: error
plan_id: EXAMPLE-PLAN
error: unresolvable_step
message: "phase_6 step `plan-marshall:ghost-review` in marshal.json is unresolvable: step `plan-marshall:ghost-review` referenced by `marshal.json` is not a discovered ext-point-finalize-step implementor — the id resolves to no built-in finalize step, project-local skill, or bundle discovery-registry entry"
phase: phase_6
step_id: "plan-marshall:ghost-review"
marshal_key: "plan-marshall:ghost-review"
```

### read

Read the manifest as TOON.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

**Output** (TOON): the full manifest content (see schema above), wrapped with `status: success` and echoed `plan_id`.

### lanes preview

Resolve all three execution-profile postures (`minimal` / `auto` / `full`) over the configured phase-6 candidate step list and return them — with per-posture step counts and summed token costs — in **one TOON**. This is the single projection the `phase-1-init` posture dialogue reads to show each posture's concrete kept-step set and cost preview; because it shares `_apply_lane_resolution` with `compose`, the dialogue preview and the executed flow cannot diverge. The lane contract (the closed `class` enum, the class→default-tier table, the resolution lattice) is owned by [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md).

`full` and `minimal` are pure config projections (the lane cutoff over the configured candidates); `auto` additionally drops every `full`-tier element. Each posture's `cost_sum_tokens` is `Σ(resolved element cost_size → cost_size_token_table)` (the six-size table, default `{XS:5K, S:25K, M:60K, L:130K, XL:260K, XXL:520K}`, overridable at `plan.phase-5-execute.cost_size_token_table`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  lanes preview --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
lanes:
  minimal:
    phase_6_steps[6]: [ push, create-pr, ci-verify, branch-cleanup, record-metrics, archive-plan ]
    phase_6_steps_count: 6
    cost_sum_tokens: 30000
  auto:
    phase_6_steps[12]: [ ... ]
    phase_6_steps_count: 12
    cost_sum_tokens: 700000
  full:
    phase_6_steps[14]: [ ... ]
    phase_6_steps_count: 14
    cost_sum_tokens: 960000
```

### record-step

Append one per-step execution record (outcome + token attribution) to the manifest's `execution_log[]` section. The manifest MUST already exist (composed by `phase-4-plan` Step 8b); `record-step` returns `file_not_found` otherwise.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  record-step \
  --plan-id {plan_id} \
  --step-id {step_id} \
  --phase {5-execute|6-finalize} \
  --outcome {executed|skipped|error} \
  [--total-tokens {N}] \
  [--tool-uses {N}] \
  [--duration-ms {N}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--step-id` (required): Step identifier being recorded (e.g., a phase-5 verification step ID or a phase-6 finalize step ID)
- `--phase` (required): `5-execute|6-finalize` — the phase the step ran in
- `--outcome` (required): `executed|skipped|error` — whether the step ran, was skipped, or errored
- `--total-tokens` (optional, default `0`): Total tokens attributed to the step
- `--tool-uses` (optional, default `0`): Tool-use count attributed to the step
- `--duration-ms` (optional, default `0`): Wall-clock duration in milliseconds

Each call appends exactly one row to `execution_log[]` (an ordered append log, not a keyed map) and emits one `decision.log` line via the in-process `_emit_decision_log` helper. Re-invocation appends another row deterministically, so every dispatch of a step is recorded. This makes per-step execution metadata loggable per-plan deterministically rather than relying on the fragile orchestrator `<usage>`-forwarding boundary call.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
file: execution.toon
recorded: true
step_id: quality_check
phase: 5-execute
outcome: executed
total_tokens: 12000
tool_uses: 8
duration_ms: 4200
timestamp: 2026-06-08T10:15:00+00:00
execution_log_count: 1
```

On a missing manifest: `status: error`, `error: file_not_found`. On an invalid `--phase` / `--outcome` value: `status: error`, `error: invalid_phase` / `invalid_outcome`.

### step-params get

Return a step's snapshotted param object from the plan-local manifest — a literal file read of the compose-time snapshot under `body[phase].step_params[step_id]`, never a marshal.json read. The one-stop read that phase-5/6 runtime consumers use instead of per-field `manage-config get --field` reads of step-owned params.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get \
  --plan-id {plan_id} \
  --phase {5-execute|6-finalize} \
  --step-id {step_id}
```

Returns `{phase, step_id, params}` (the complete snapshotted param object). An absent step id (no `step_params` entry) → `status: error`, `error: step_not_found`. A missing manifest → `error: file_not_found`; an invalid `--phase` → `error: invalid_phase`.

### step-params set

Write a per-plan param override into the manifest's `step_params` snapshot — a plan-local override that wins over the marshal.json compose-time default for subsequent `step-params get` reads. Operates on the persisted manifest only, never on marshal.json.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params set \
  --plan-id {plan_id} \
  --phase {5-execute|6-finalize} \
  --step-id {step_id} \
  --param {key} \
  --value {value}
```

The value is coerced (`true`/`false` → bool; integer literal → int; else string), the param is merged into the step's param object (siblings preserved), and the updated `params` object is returned. An absent step id → `error: step_not_found`; a missing manifest → `error: file_not_found`; an invalid `--phase` → `error: invalid_phase`.

### validate

Verify the manifest schema and that all step IDs appear in the caller-supplied allow-list CSVs.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate --plan-id {plan_id} \
  [--phase-5-steps {step1,step2,...}] \
  [--phase-6-steps {step1,step2,...}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase-5-steps` (optional): Comma-separated allowed Phase 5 step IDs to validate against. This is `validate`'s own caller-supplied allow-list — a separate surface from `compose`'s same-named fallback-only candidate flag. Because `compose`'s `execution_tier` routing can append `verify:{verb}` step IDs that were never in the configured candidate list, the allow-list must also cover those compose-routed IDs.
- `--phase-6-steps` (optional): Comma-separated allowed Phase 6 step IDs to validate against (same allow-list semantics)

Omitting a flag skips that phase's step-ID check (schema checks always run).

**Prefix-agnostic step-ID comparison**: the unknown-ID check strips the optional `default:` prefix from BOTH the allowed set and the manifest step IDs before the set-membership test, so a bare manifest ID (e.g. `verify:module-tests`) validates against a `default:`-prefixed allowed-list entry (e.g. `default:verify:module-tests`) and vice versa. `project:` / `bundle:skill` prefixes are preserved verbatim, so external steps still compare exactly. This is what lets the composer's boundary-normalized (bare) manifest IDs validate against an allowed-list passed in either prefixed or bare form.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
valid: true
phase_5_unknown_steps_count: 0
phase_6_unknown_steps_count: 0
```

On failure: `status: error`, `error: invalid_manifest`, plus a `message` and per-section unknown-step list.

### Manifest-on-Write Semantics

The execution manifest is a **write-time snapshot**, not a runtime view. Two halves, both load-bearing — the manifest's design depends on both:

1. **Baked at write time.** `compose` reads the **then-current** plugin cache state (decision-rules tables, candidate step lists from `marshal.json`, recipe-key mappings, default `Phase 5` / `Phase 6` step sets) and writes a fixed list of step IDs into `.plan/local/plans/{plan_id}/execution.toon`. The composer is `phase-4-plan` Step 8b at plan-write time; `phase-5-execute` MAY re-invoke `compose` to amend during its own loop, but every invocation is idempotent — the file is overwritten in full from the inputs supplied to that call.
2. **Not re-resolved at read time.** `read` is a literal file load. `phase-5-execute` and `phase-6-finalize` consume `phase_5.verification_steps` and `phase_6.steps` verbatim from the persisted file — they do NOT re-derive the list from current decision rules, do NOT re-consult `marshal.json` for fresh candidate sets, and do NOT re-apply the decision matrix at consumption time. The manifest IS the contract for the running plan.

**Consequence — `Phase 6` reads the pre-change snapshot**: a plan that modifies a decision rule, a `marshal.json` default, the seven-row decision matrix, or any other manifest-composer input still sees the **pre-change** manifest shape when `phase-6-finalize` reads it back, even after `/sync-plugin-cache` has run and the Claude Code session has been restarted. The cache sync and session restart fix the manifest's **future composition** (subsequent plans that invoke `compose`), not the current plan's already-written `execution.toon`.

Meta-projects that author marketplace bundles maintain their own self-host fence to guard against this class of staleness in their own finalize phase; consumer projects of plan-marshall do not encounter the failure mode because their plans do not modify the manifest composer's own resolution roots. Plans that intend to use a newly-introduced step or a newly-changed decision rule in their own finalize phase MUST either (a) re-run `compose` after the cache sync and session restart (re-composition re-reads the now-current cache state) or (b) edit `execution.toon` directly with the intended step list. The `validate` and `validate-loadable` operations remain valid post-edit; both check the persisted file, not a re-derived view.

The write-time-snapshot model is a deliberate design choice — it makes the manifest diffable, auditable, and resumable across crashes. Re-resolving at read time would couple every Phase 6 step dispatch to the in-memory decision rules, which is precisely the coupling the manifest exists to break.

### validate-loadable

Verify that the standards file backing each `phase_6.steps` entry is present and readable. This is the loadability fail-fast guard consumed by `phase-6-finalize` Step 1.5 to catch self-modifying plans that delete a built-in step's standards file without sweeping `marshal.json`.

```bash
# Single-step form
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate-loadable --plan-id {plan_id} --step-id {step_id}

# Bulk form — validate every step in manifest.phase_6.steps
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate-loadable --plan-id {plan_id} --all
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--step-id` (mutually exclusive with `--all`): A single step id to check (bare name `push` or prefixed `default:push`; both forms accepted)
- `--all` (mutually exclusive with `--step-id`): Walk every entry in `manifest.phase_6.steps` and report per-step results

**Scope**: built-in steps only (bare names that resolve to `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/{name}.md`). External steps (`project:` / `bundle:skill`) are out of scope — `validate-loadable` returns `loadable: true` for them with no further check, on the rationale that their loadability is the host plugin cache's responsibility and a missing skill surfaces at `Skill: {ref}` dispatch time as a different failure mode.

**Output (single-step form)**:
```toon
status: success
plan_id: EXAMPLE-PLAN
step_id: push
standards_path: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md
loadable: true
```

When the standards file is missing or unreadable, `loadable: false` and a `message` field carries the canonical actionable phrasing:
```toon
status: success
plan_id: EXAMPLE-PLAN
step_id: missing-step
standards_path: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/missing-step.md
loadable: false
message: "step `missing-step` referenced by `marshal.json` is missing standards file `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/missing-step.md` — the plan likely deleted the file without sweeping `marshal.json`"
```

**Output (bulk form)**: a `results[N]` table with one row per manifest step plus an `unloadable_count` summary, e.g.:
```toon
status: success
plan_id: EXAMPLE-PLAN
unloadable_count: 1
results[3]{step_id,standards_path,loadable,message}:
  push,marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md,true,
  create-pr,marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md,true,
  ghost-step,marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ghost-step.md,false,"step `ghost-step` referenced by `marshal.json` is missing standards file `…ghost-step.md` — the plan likely deleted the file without sweeping `marshal.json`"
```

The bulk form requires the manifest to exist on disk; if it does not, the script returns the standard `file_not_found` error.

---

## Scripts

**Script**: `plan-marshall:manage-execution-manifest:manage-execution-manifest`

| Command | Parameters | Description |
|---------|------------|-------------|
| `compose` | `--plan-id --change-type --track --scope-estimate [--recipe-key] [--affected-files-count] [--phase-5-steps] [--phase-6-steps] [--commit-and-push] [--envelope-count] [--aspect]` | Compose and write execution.toon (`--phase-5-steps`/`--phase-6-steps` are fallback-only — `marshal.json` is the authoritative candidate source) |
| `read` | `--plan-id` | Read manifest as TOON |
| `lanes preview` | `--plan-id [--phase-6-steps]` | Resolve the minimal/auto/full phase-6 step sets + cost sums in one TOON (the posture-dialogue projection) |
| `record-step` | `--plan-id --step-id --phase {5-execute\|6-finalize} --outcome {executed\|skipped\|error} [--total-tokens] [--tool-uses] [--duration-ms]` | Append a per-step execution-log row (outcome + token attribution) to execution.toon |
| `step-params get` | `--plan-id --phase {5-execute\|6-finalize} --step-id` | Return a step's snapshotted param object from the manifest (plan-local read) |
| `step-params set` | `--plan-id --phase {5-execute\|6-finalize} --step-id --param --value` | Write a per-plan param override into the manifest snapshot |
| `validate` | `--plan-id [--phase-5-steps] [--phase-6-steps]` | Validate manifest schema + step IDs against the caller-supplied allow-list CSVs (a separate surface from compose's candidate source) |
| `validate-loadable` | `--plan-id (--step-id ID \| --all)` | Verify standards file presence for built-in `phase_6.steps` entries |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `file_not_found` | execution.toon doesn't exist (read/validate) |
| `invalid_change_type` | --change-type not in the valid enum |
| `invalid_scope_estimate` | --scope-estimate not in the valid enum |
| `invalid_track` | --track not `simple` or `complex` |
| `invalid_phase` | `record-step` --phase not `5-execute` or `6-finalize` |
| `invalid_outcome` | `record-step` --outcome not `executed`, `skipped`, or `error` |
| `invalid_manifest` | Manifest schema invalid or step IDs unknown; or `step-params set` target section malformed |
| `unresolvable_step` | `compose` — a FINAL emitted phase-5/6 step id resolves to no built-in doc, project-local skill, or bundle discovery-registry entry (fail-loud; names the offending `marshal.json` key and phase) |
| `invalid_arguments` | `validate-loadable` invoked without exactly one of `--step-id` / `--all` |
| `step_not_found` | `step-params get`/`set` `--step-id` has no snapshotted params in the manifest for the given phase |

---

## Canonical invocations

The canonical argparse surface for `manage-execution-manifest.py`. The D4 plugin-doctor
analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for
markdown notation occurrences across the marketplace. Consuming skills xref this
section by name (e.g., "see `manage-execution-manifest` Canonical invocations →
`compose`") instead of restating the command inline.

### compose

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest compose \
  --plan-id PLAN_ID \
  --change-type {analysis|feature|enhancement|bug_fix|tech_debt|verification} \
  --track {simple|complex} \
  --scope-estimate {none|surgical|single_module|multi_module|broad} \
  [--recipe-key KEY] [--affected-files-count N] \
  [--phase-5-steps LIST] [--phase-6-steps LIST] \
  [--commit-and-push {true|false}] [--envelope-count N] \
  [--aspect {analysis|planning|implementation}]
```

`--phase-5-steps` / `--phase-6-steps` on `compose` are **fallback-only** (tests / no-marshal contexts): with a readable `marshal.json` the composer sources its candidate lists authoritatively from `plan.phase-5-execute.verification_steps` / `plan.phase-6-finalize.steps` and ignores the CSVs, so in an inited project forwarding a CSV cannot inject a plan-scoped candidate. The same-named flags on `validate` are a different surface — see `validate` below.

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest read \
  --plan-id PLAN_ID
```

### lanes preview

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest lanes preview \
  --plan-id PLAN_ID [--phase-6-steps PHASE_6_STEPS]
```

### record-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest record-step \
  --plan-id PLAN_ID \
  --step-id STEP_ID \
  --phase {5-execute|6-finalize} \
  --outcome {executed|skipped|error} \
  [--total-tokens N] [--tool-uses N] [--duration-ms N]
```

### validate

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest validate \
  --plan-id PLAN_ID \
  [--phase-5-steps LIST] [--phase-6-steps LIST]
```

On `validate` the `--phase-5-steps` / `--phase-6-steps` CSVs are the **caller-supplied allow-list** of permitted step IDs — a separate input from `compose`'s candidate source (where the same-named flags are fallback-only against the marshal-authoritative seeding above). Omitting a flag skips that phase's step-ID check; when supplied, every manifest step ID must appear in the allow-list (prefix-agnostic on `default:`; `project:` / `bundle:skill` prefixes compare verbatim) or validation fails with `invalid_manifest`. Because `compose`'s `execution_tier` routing can append `verify:{verb}` step IDs that were never in the configured candidate list, the allow-list must also cover the compose-routed `verify:{verb}` IDs.

### validate-loadable

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest validate-loadable \
  --plan-id PLAN_ID \
  (--step-id STEP_ID | --all)
```

`--step-id` and `--all` are mutually exclusive; exactly one is required.

### step-params get

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest step-params get \
  --plan-id PLAN_ID --phase {5-execute|6-finalize} --step-id STEP_ID
```

### step-params set

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest step-params set \
  --plan-id PLAN_ID --phase {5-execute|6-finalize} --step-id STEP_ID --param PARAM --value VALUE
```

---

## Decision Rules

The seven-row decision matrix is documented in [standards/decision-rules.md](standards/decision-rules.md). The matrix maps the inputs (`change_type`, `track`, `scope_estimate`, `recipe_key`, `affected_files_count`) to:

- `phase_5.early_terminate` (true/false)
- The subset of `phase_5.verification_steps` chosen from the candidate set
- The subset of `phase_6.steps` chosen from the candidate set

For each rule fired, `compose` emits one `decision.log` entry — written in-process via `plan_logging.log_entry` (NOT by shelling back out to the executor) — with the canonical prefix `(plan-marshall:manage-execution-manifest:compose)` and the rule name. The in-process write resolves the plan dir the same way the manifest write does, so the line always lands in the plan's own `logs/decision.log`; the prior executor-subprocess path silently dropped every line because the composer runs from the plugin cache, outside the project tree where `.plan/execute-script.py` lives. This satisfies the request example "one entry per decision".

### Scope-gated phase-6 filtering (`scope_gated_finalize`)

Before the seven-row matrix, the composer applies a scope-gated pre-filter that drops heavyweight phase-6 review/audit steps based on `scope_estimate`:

- **`surgical`** — drops `plan-marshall:plan-retrospective`, pre-submission-self-review, and `project:finalize-step-plugin-doctor`. Every bare and prefixed form is matched: for pre-submission-self-review this covers the built-in `default:pre-submission-self-review` (normalized to bare `pre-submission-self-review` at intake). The candidate list is `default:`-namespace-normalized at intake, but `project:` / `bundle:skill` prefixes are preserved verbatim — so `plan-marshall:plan-retrospective` and `project:finalize-step-plugin-doctor` are matched by their full prefixed form, not a bare normalization.
- **`single_module`** — drops only `plan-marshall:plan-retrospective`.
- **`multi_module` / `broad` / `none`** — no implicit subtraction; the full candidate set is retained.

`automatic-review` is NEVER dropped by the implicit scope gate: its presence is governed purely by its configured `lane` and lane tier, so the implicit scope gate must not drop it. The only path that suppresses `automatic-review` at the scope gate is the explicit `drop_review_on_scope_gate` escape hatch.

**`drop_review_on_scope_gate`** — a step-owned param of `default:pre-submission-self-review`, read from `marshal.json` at `plan.phase-6-finalize.steps['default:pre-submission-self-review'].drop_review_on_scope_gate` (default `false`). When `true` **and** the plan is itself scope-gated (`scope_estimate ∈ {surgical, single_module}`), the scope gate additionally drops `automatic-review` — the single deliberate path that suppresses the bot-review gate at the scope stage, explicitly opted into. The override is scoped, not global: on `multi_module` / `broad` / `none` plans it is inert, so flipping the project-wide knob can never silently disable bot review on a large plan. The default (`false`) keeps `automatic-review` governed by its `lane` alone.

The composer emits one `decision.log` line per scope-gated subtraction (canonical prefix `(plan-marshall:manage-execution-manifest:compose) scope_gated_finalize subtraction`) and surfaces `scope_gated_finalize_dropped` and `drop_review_on_scope_gate` in the `compose` result for observability.

### Generic footprint pre-filter for canonical-verify steps (`canonical_verify_inactive`)

After the seven-row matrix and `execution_tier` routing produce the final `phase_5.verification_steps` list, the composer applies a canonical-agnostic footprint pre-filter: a `default:verify:{canonical}` step whose derived role is a footprint-gated whole-tree role (`integration` / `e2e`) is dropped when the live footprint is non-empty AND carries no path of that role. The core roles (`quality-gate` / `module-tests` / `coverage`) are never footprint-gated. The pre-filter is a no-op when the footprint is empty (early compose, before the worktree is materialized), so every canonical survives until a re-compose can observe the real footprint. The composer emits one `decision.log` line when at least one step is dropped (canonical prefix `(plan-marshall:manage-execution-manifest:compose) canonical_verify_inactive`). The full rule and the safety-against-compose-time-emptiness rationale are documented in [standards/decision-rules.md](standards/decision-rules.md) § "Generic footprint pre-filter".

### Request-aspect step dropping (`aspect_step_dropping`)

After the canonical-verify footprint pre-filter produces the final `phase_5.verification_steps` list, the composer applies the **request-aspect step-dropping** pass driven by the optional `--aspect` input (the resolved aspect from the `manage-config aspect-classify` verb). When `aspect ∈ {analysis, planning}`, every canonical-verify step whose derived matrix role is a build / quality-gate / test role (`quality-gate` / `module-tests` / `coverage`) is dropped from the phase-5 list. The rationale is the inverse of the footprint pre-filter: an `analysis` or `planning` request carries no production / test footprint to gate, so running (and failing) build / quality-gate / test commands against a code-free change is pure waste — the aspect signal lets the composer drop those gates up front rather than relying on a footprint that may not yet exist at compose time.

An `implementation` aspect (the classifier's safe sub-threshold fallback — any request below the `>= 0.7` aspect-classify threshold defaults to `implementation`) and an absent `--aspect` are no-ops: every build/verify gate is retained. The drop is role-driven (via the same `_role_of` derivation the footprint pre-filter uses) and canonical-agnostic — it adds no per-canonical branch. External (`project:` / `bundle:skill`) steps and any step whose role is unrecognized are passed through untouched. The composer emits one `decision.log` line when at least one step is dropped (canonical prefix `(plan-marshall:manage-execution-manifest:compose) aspect_step_dropping`) and surfaces `aspect` and `aspect_step_dropping_dropped` in the `compose` result for observability.

### Command-level execution_tier routing (`execution_tier_routing`)

Before the per-step stamping below, the composer walks every task's `verification.commands` and routes each build command by its resolved `execution_tier` (see [standards/decision-rules.md](standards/decision-rules.md) § "execution_tier Routing" for the full predicate). For `orchestrator`-tier commands the verb maps to a bare phase-5 step ID: the four canonical verbs route through the `_VERB_TO_PHASE_5_STEP` fast path (`quality-gate` / `verify` / `module-tests` / `coverage`), and **every other parseable verb generalizes to the bare `verify:{verb}` step** — the command is removed from the task in both cases, so no leaf ever runs an orchestrator-tier command inline. Each non-canonical routed verb is named in its own `decision.log` line (canonical prefix `(plan-marshall:manage-execution-manifest:compose) execution_tier routing`), in addition to the summary line carrying `mutated_tasks` and the final step list.

**Raw-shell limitation**: only commands in the canonical Bucket B build shape (`python3 .plan/execute-script.py plan-marshall:build-*:... run --command-args "..."`) carry a parseable verb. A raw-shell or non-`plan-marshall:build-` command that the tier classifier nonetheless labels `orchestrator` cannot be verb-routed — it is deliberately left in the task's `verification.commands` so the mapping mismatch stays observable at the next compose, rather than being silently dropped.

**Interaction with per-step stamping**: routing runs first and may append `verify:{verb}` entries to `phase_5.verification_steps`; the stamping pass below then resolves a tier for the FINAL list, so every routed step — canonical or generalized — receives a stamped `{step_id, tier}` record. A generalized `verify:{verb}` whose canonical is unresolvable stamps to the `per_task` safe floor per the stamping rule.

### Per-step execution_tier stamping (`step_execution_tier`)

After the request-aspect step-dropping pass produces the FINAL `phase_5.verification_steps` list, the composer resolves each selected step's `execution_tier` and stamps a `phase_5.step_execution_tier` record list (one `{step_id, tier}` object per verification step). Each built-in canonical-verify step (`verify:{canonical}`) is resolved via a whole-tree `architecture resolve --command {canonical}`, reading the `execution_tier` field the resolve TOON emits; every other step id (an external `project:` / `bundle:skill` step, or a `verify:{canonical}` whose canonical is unresolvable) defaults to `per_task`. The list is total over `verification_steps` — the composer never emits an unresolved tier, and `per_task` is the safe floor (the leaf runs the step inline, matching the pre-stamp behaviour).

This is the **compose-time structural guard** that supersedes the prose-only leaf-no-background-build invariant (proven insufficient over repeated observations): because the tier is a manifest fact, `phase-5-execute` runs only `per_task` steps inline and routes every `orchestrator`-tier step to the main-context orchestrator's `await-long-running` detach-and-notify seam — the only component permitted to background a build. A dispatched leaf therefore structurally never receives a long build it would background-and-lose. The composer emits one `decision.log` line naming each step's resolved tier (canonical prefix `(plan-marshall:manage-execution-manifest:compose) step_execution_tier stamping`) and surfaces `step_execution_tier` in the `compose` result. The full rule is documented in [standards/decision-rules.md](standards/decision-rules.md) § "execution_tier stamping" and the leaf-boundary contract in [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md) § "Leaf cannot reap a backgrounded build".

### phase-6-finalize ceremony-gate selection (`ceremony_finalize_selection`)

After the seven-row matrix produces the final `phase_6.steps` (and after `execution_tier` routing), and before the execution-profile lane resolution, the composer applies the four `plan.phase-6-finalize` ceremony gates to force their finalize steps in or out. Each gate's run decision is derived from its owning finalize step's per-element `lane` override (`off→never`, `minimal→always`, `auto`/absent→`auto`):

| Gate | Owning step (its `lane` override) | `never` → drop · `always` → force-include · `auto` → defer |
|------|-----------------------------------|------------------------------------------------------------|
| `self_review` | `default:pre-submission-self-review` | force the pre-submission structural + cognitive self-review |
| `qgate` | `default:pre-push-quality-gate` | force the finalize blocking-findings re-capture |
| `simplify` | `default:finalize-step-simplify` | force the holistic post-implementation simplification sweep |
| `security_audit` | `default:finalize-step-security-audit` | force the proactive security sweep |

`always` is the only path that re-adds a step the relevant pre-filter dropped — an operator-set `always` (via `lane: minimal`) overrides the implicit gate. All four gates now ride the same per-element `lane` override channel: each gate's decision is derived from `steps[<owner>].lane` (via `_read_finalize_gates`), with no flat phase-level `qgate` sibling and no step-owned run-at-all param. The transform NEVER touches `automatic-review` — its gate map contains only the four ceremony steps, so `automatic-review` remains governed purely by its own `lane` through the execution-profile lane-resolution pass, with no separate force-add guard.

The composer emits one `decision.log` line per forced change (canonical prefix `(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection`) and surfaces `ceremony_finalize_gates`, `ceremony_finalize_forced_in`, and `ceremony_finalize_forced_out` in the `compose` result for observability. The full rule (gate→step map, `automatic-review` carve-out, post-matrix-transform rationale) is documented in [standards/decision-rules.md](standards/decision-rules.md) § "plan.phase-6-finalize Selection". The per-element `lane` override schema is owned by [`manage-config/standards/data-model.md`](../manage-config/standards/data-model.md) § phase-6-finalize and [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md).

### Execution-profile lane resolution (`lane_resolution`)

After the change-type / scope pre-filters and `ceremony_finalize_selection` produce the `phase_6.steps` list, and **before** the frontmatter-order sort, the composer applies the execution-profile lane cutoff. The posture is read from `status.metadata.execution_profile` (absent → `full` → no pruning, preserving the pre-lane composition path for every plan that never chose a posture). Each lane-participating element self-declares a `lane:` frontmatter block (`class` / `tier` / `prunable_when` / `cost_size`); the closed enums and the class→default-tier table are owned by [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md). Per element the composer resolves the effective tier (per-element `marshal.json` `lane` override ▸ declared `lane.tier` ▸ class default) and keeps the element iff `effective_tier ⊑ posture` on `minimal ⊏ auto ⊏ full`:

- `minimal` keeps only the tier-`minimal` floor (`core` / `derived-state` plus the `minimal`-deviated lessons steps);
- `auto` additionally keeps tier-`auto` elements and drops tier-`full` ones (`security-audit`, `plan-retrospective`);
- `full` keeps everything (a no-op).

An element with no `lane:` block is not lane-participating and is always kept. A weakening `off` override of a `derived-state` / `core` floor element is **immune — the `off` is ignored and the element stays kept at its class-default tier** (§5 of the lane-selection design — `minimal` must never drop required derived state; a weakening `off` on a mandatory floor element cannot disable it, and the composer surfaces an informational note recording the neutralization). `automatic-review` participates in this pass like any other adversarial lane element — its keep/drop is governed purely by its configured `lane` and lane tier, with no separate downstream force-add guard, so a `minimal` posture or an `off` override that drops it is honored as the operator's decision (adversarial elements keep honoring `off` as a real opt-out). The q-gate is never a phase-6 finalize step, so it is never lane-pruned. The composer emits one `decision.log` line when at least one step is dropped (canonical prefix `(plan-marshall:manage-execution-manifest:compose) lane_resolution`), one line per lane warning (including the immune-`off` informational note), and surfaces `execution_profile`, `lane_dropped`, and `lane_warnings` in the `compose` result. `lane_warnings` has **two producers**: the lane resolution itself (the immune-`off` neutralization note) and the **ceremony pre-filter** — when the `simplify_inactive` / `security_audit_inactive` pre-filter drops a step that the operator's selected posture/lane would have included (and the ceremony `always` gate did not force it back in), the composer appends a `{step, warning}` entry naming the ceremony pre-filter, not the lane, as the remover, so the drop is never silent (the `simplify_omitted` / `security_audit_omitted` booleans remain in the result unchanged). The full rule is documented in [standards/decision-rules.md](standards/decision-rules.md) § "Execution-profile lane resolution".

**Twice-compose timing.** `compose` runs twice (lane design §4.5): once at **init** (`phase-1-init`, provisional `auto` footprint prunes) and once at **end-of-phase-4** (idempotent re-compose with firm signals). The posture and the `minimal`/`full` shapes are fixed at init and never change on the second call; only `auto`'s footprint-gated prunes can move (in the safe, more-validation direction), and that refinement is **logged, never re-prompted**.

### Frontmatter-order sort (`frontmatter_order_sort`)

After the execution-profile lane resolution (the last transform to add or drop a step) and before manifest persistence, the composer reorders the final `phase_6.steps` into ascending frontmatter `order` via `_sort_steps_by_frontmatter_order` (`_manifest_validation.py`). The stable sort reorders every order-resolvable step while entries whose `_resolve_step_order` is `None` (external `bundle:skill` steps, non-string entries) keep their original index, so `archive-plan` (order 1000) is the terminal barrier regardless of the marshal.json seed order — the single choke-point correcting the sync-defaults append misordering and any other upstream seed corruption. It is also the sole ordering authority for `automatic-review` (order 30, sorted before the plan-mutating tail), so no separate placement validator is required. The transform is unconditional, emits no dedicated `decision.log` line, and is the compose-time companion of the `_check_ascending_order` validator. The full rule (pin semantics, barrier consequence, insertion-helper interaction) is documented in [standards/decision-rules.md](standards/decision-rules.md) § "Frontmatter-Order Sort".

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-4-plan` | compose | Emit manifest as terminal step before phase transition (Step 8b); the compose call also snapshots each selected step's resolved params into `phase_{5,6}.step_params` |
| `phase-5-execute` | record-step, step-params set | Append a per-step execution-log row after each verification step dispatches; optionally write a per-plan step-param override |
| `phase-6-finalize` | record-step, step-params set | Append a per-step execution-log row after each finalize step dispatches; optionally write a per-plan step-param override |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-5-execute` | read, step-params get | Read `phase_5.early_terminate`, `phase_5.envelope_count`, and `phase_5.verification_steps` to drive envelope and verification dispatch (an absent `envelope_count` is treated as `1`); read per-step params from the plan-local snapshot |
| `phase-6-finalize` | read, step-params get | Read `phase_6.steps` to drive the finalize-step dispatch loop; read each step's params via the one-stop `step-params get` (review / branch-cleanup / sonar consumers) |
| `workflow-integration-sonar` | step-params get | Read the `default:sonar-roundtrip` step's `ce_wait_timeout_seconds` / `touched_file_cleanup` / `do_transition` params from the plan-local snapshot |
| `plan-retrospective` | read | Cross-check manifest assumptions against end-of-execute diff |

## Related

- `manage-references` — Plan-scoped references including `affected_files` and `scope_estimate` consumed by the composer
- `manage-logging` — Decision-log target for the per-rule reasoning entries emitted by `compose`
- `manage-config` — Source of `marshal.json` candidate Phase 5/6 step lists
- [standards/self-blocking-guards.md](standards/self-blocking-guards.md) — Generalised meta-pattern for enforcement mechanisms that ship inside the marketplace they police (anchor-relative insertion contracts and override-flag fallback). Pattern-level reference, not bot-enforcement-specific implementation notes.
