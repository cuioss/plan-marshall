---
name: manage-execution-manifest
description: Compose, read, and validate the per-plan execution manifest that drives Phase 5 verification and Phase 6 finalize step selection
user-invocable: false
mode: script-executor
scope: plan
---

# Manage Execution Manifest Skill

Compose, read, and validate the per-plan **execution manifest** — a small declarative artifact emitted at the end of `phase-4-plan` that names the exact Phase 5 verification steps and Phase 6 finalize steps for this plan. Phases 5 and 6 become dumb manifest executors; per-doc skip logic in their standards is removed in favor of this single source of truth.

This skill is **script-only**: it has no user-invocable command and is not loaded into LLM context via `Skill:` directives. It is invoked exclusively through the 3-part script notation `plan-marshall:manage-execution-manifest:manage-execution-manifest`. Registration in `plugin.json` is OPTIONAL for such a skill: `plugin-doctor`'s `plugin-json-orphan-component` rule EXEMPTS a `user-invocable: false` skill from the registration requirement rather than forbidding it from registering. This bundle's `plugin.json` does list `./skills/manage-execution-manifest`.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- The manifest file is the single source of truth for Phase 5/6 step selection — every decision MUST be reflected in the manifest, and every reasoning MUST be logged via `manage-logging decision`.
- The manifest stays lean and diffable. Do not embed reasoning, timestamps, or free-text fields — push those to `decision.log`.
- `compose` is idempotent: re-invocation overwrites the previous manifest. Callers responsible for re-entry semantics.
- The six-row decision matrix is authoritative. See [decision-rules.md](standards/decision-rules.md) for the canonical table.

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
    - verify:quality-gate
    - verify:module-tests
    - verify:coverage
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
  - push,6-finalize,executed,unmeasured,unmeasured,unmeasured,2026-06-08T10:44:00+00:00
```

The three rows differ in kind, not only in value. The `skipped` row carries a MEASURED `0` — its caller passed `--total-tokens 0` because the step genuinely consumed nothing — while the `push` row carries `unmeasured` because its caller ran the step inline, had no `<usage>` envelope to forward, and OMITTED the flags. See [standards/manifest-schema.md](standards/manifest-schema.md) § "`execution_log[]` — the per-step execution log".

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | int | Schema version (currently `1`) |
| `plan_id` | string | Plan identifier (echo) |
| `phase_5.early_terminate` | bool | If `true`, Phase 5 transitions directly to Phase 6 without running tasks (analysis-only plans with empty affected_files) |
| `phase_5.envelope_count` | int | Number of phase-5 `execution-context` envelopes the orchestrator should plan for. Written by `compose` from the optional `--envelope-count` input; defaults to `1` (a single budget-bounded envelope greedily drives the task loop) when the input is absent. A manifest composed before this field existed has no `phase_5.envelope_count` key, and every reader interprets an absent value as the same `1` default — so reads stay backward-compatible. |
| `phase_5.verification_steps` | list[string] | Ordered list of Phase 5 verification step IDs. Every built-in verify step is a parameterized canonical-verify step, so on the marshal.json compose path these are `verify:{canonical}` ids (e.g. `verify:quality-gate`, `verify:module-tests`, `verify:coverage`) — `compose` boundary-normalizes each candidate with `canonicalize_step_key`, which strips a leading `default:` and nothing else. The `--phase-5-steps` CSV fallback forwards its argument verbatim, so a caller without a marshal.json can persist bare `{canonical}` names; readers accept both. Empty list means no verification needed (e.g., docs-only plans) |
| `phase_5.step_execution_tier` | list[object] | **Advisory** per-step `execution_tier` snapshot — one `{step_id, tier}` object per `phase_5.verification_steps` entry, in list order. `tier` is `per_task` (the step fit inside the Bash ceiling at compose) or `orchestrator` (it exceeded the ceiling, so the orchestrator's `await-long-running` seam owns it). Written by `compose` via `architecture resolve` per step; the list is total over `verification_steps` and every entry carries a resolved tier (unresolved/absent defaults to `per_task`). A record list rather than a keyed map because a step id (`verify:quality-gate`) contains a colon, which does not round-trip as a TOON object key. **Not the routing authority**: the tier derives from the adaptive learned build duration, so a ceiling-adjacent step's tier legitimately moves between compose and execute — the leaf re-resolves it live and routes on that verdict (see `phase-5-execute/standards/canonical_verify.md` § Workflow and `ref-workflow-architecture/standards/agents.md` § "Leaf cannot reap a backgrounded build"). |
| `phase_6.steps` | list[string] | Ordered list of Phase 6 finalize step IDs to dispatch. Subset of the canonical step set: `push`, `create-pr`, `automated-review`, `sonar-roundtrip`, `lessons-capture`, `adr-propose`, `branch-cleanup`, `archive-plan`, `record-metrics`, `lessons-integration`. CI completion is a dispatcher-resolved precondition declared via `requires: [ci-complete]` on consumer step frontmatters (see `phase-6-finalize/SKILL.md` Step 3 § "Precondition resolution") — it is not itself a step in the canonical set. |
| `phase_6.candidate_steps` | list[string] | The phase-6 candidate set this compose selected FROM, snapshotted **before** any pre-filter or decision-matrix row subtracted from it, boundary-normalized exactly like `phase_6.steps`. Written by `compose`; read only by `reconcile`, which diffs it against live configuration to tell a candidate that is NEW since compose (owed a backfill) from one the matrix considered and deliberately dropped (must stay dropped). The emitted `phase_6.steps` cannot serve that purpose — it is the post-subtraction result, so "in live config but not in the manifest" would match both cases. A manifest composed before this field existed has no `phase_6.candidate_steps` key; `reconcile` then reports `backfill_determinable: false` rather than guessing. |
| `phase_5.step_params` | object | Per-step param snapshot for the selected Phase 5 verify steps, keyed by the (bare) in-manifest step id; each value is the step's resolved param object snapshotted from the marshal.json keyed map at compose time. Verify steps own no params, so values are typically `{}`. Read via `step-params get`; per-plan overridable via `step-params set`. |
| `phase_6.step_params` | object | Per-step param snapshot for the selected Phase 6 finalize steps, keyed by the (bare) in-manifest step id; each value is the step's resolved param object snapshotted from the marshal.json keyed map at compose time (e.g. `branch-cleanup` carries `pr_merge_strategy` / `final_merge_without_asking` / `auto_rebase_threshold`; `sonar-roundtrip` carries `touched_file_cleanup` / `do_transition` / `ce_wait_timeout_seconds`; `automated-review` carries `review_bot_buffer_seconds`). This is the **plan-local runtime source** that phase-5/6 consumers read via `step-params get` (per-plan overridable via `step-params set`), NOT the marshal.json keyed map (the compose-time default). |
| `execution_log` | list[object] | Ordered append log of per-step execution records, written one row per `record-step` invocation. Each row carries `step_id` (the dispatched step), `phase` (`5-execute` or `6-finalize`), `outcome` (`executed`/`skipped`/`loop_back`/`failed`/`error`), the token-attribution triple `total_tokens`/`tool_uses`/`duration_ms`, and an ISO-8601 `timestamp`. Each of the three token columns is **three-state**: a non-negative int is a measured value (including a measured `0`), the literal `unmeasured` is written when the caller OMITTED the flag, and any other cell is unrecognised. There is no `0` default — see [standards/manifest-schema.md](standards/manifest-schema.md) § "`execution_log[]` — the per-step execution log" for the write-side discriminator and the reader obligation. Absent until the first `record-step` call; the `compose`/`read`/`validate`/`validate-loadable` operations never read or write it. |

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
  --plan-change-type {change_type} \
  --track {simple|complex} \
  --scope-estimate {none|surgical|single_module|multi_module|broad} \
  [--recipe-key {recipe_key}] \
  [--affected-files-count {N}] \
  [--phase-5-steps {step1,step2,...}] \
  [--phase-6-steps {step1,step2,...}] \
  [--commit-and-push {true|false}] \
  [--envelope-count {N}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--plan-change-type` (required): `analysis|feature|enhancement|bug_fix|tech_debt|verification`. This is the PLAN-scoped change type — a distinct scope from a deliverable's local `change_type`. The composer reconciles it against the plan's **settled classification** at `status.metadata.change_type`: when a settled classification exists, the supplied value MUST agree with it, otherwise compose returns `change_type_scope_conflict` (naming both values) rather than silently narrowing the whole plan on a deliverable-scoped value. When no settled classification exists, the supplied value stands alone. The flag was renamed from `--change-type` so a caller cannot pass a deliverable's kind where the plan's classification is meant. See [decision-rules.md](standards/decision-rules.md) § "change_type scope reconciliation".
- `--track` (required): `simple|complex` — outline track from phase-3-outline
- `--scope-estimate` (required): `none|surgical|single_module|multi_module|broad` — from solution outline metadata (deliverable 2)
- `--recipe-key` (optional override): Forces the `recipe` rule. When omitted, the composer reads the provenance itself from `status.json::metadata.plan_source` (falling back to `metadata.recipe_key`), so lesson- and recipe-derived plans select the `recipe` rule without the caller forwarding this flag.
- `--affected-files-count` (optional, default 0): Count of affected files surfaced by the outline; used by the `early_terminate` rule
- `--phase-5-steps` (optional): Comma-separated candidate Phase 5 verification step IDs. The composer prefers `marshal.json::plan.phase-5-execute.verification_steps` (the phase-aware list-field — phase-5 reads `verification_steps`, every other phase reads `steps`; see [decision-rules.md](standards/decision-rules.md) § "Phase-aware step source"), falling back to this CSV only when no marshal.json is present. The IDs may be the legacy bare role-file forms (`default:quality_check`, …) or the parameterized canonical-verify form `default:verify:{canonical}` (e.g. `default:verify:quality-gate`, `default:verify:module-tests`, `default:verify:coverage`), whose matrix role is derived from the trailing canonical segment (see [decision-rules.md](standards/decision-rules.md) § "Role derivation for canonical-verify steps"). The decision matrix selects a subset, then the generic footprint pre-filter (§ "Generic footprint pre-filter") drops any footprint-gated whole-tree canonical (`integration` / `e2e`) that the live footprint does not exercise.
- `--phase-6-steps` (optional): Comma-separated candidate Phase 6 finalize step IDs (e.g., `push,create-pr,automated-review,sonar-roundtrip,lessons-capture,adr-propose,branch-cleanup,archive-plan`). Same fallback-only contract as `--phase-5-steps`: the composer prefers `marshal.json::plan.phase-6-finalize.steps`, consulting this CSV only when no marshal.json is present — so in an inited project the CSV cannot inject a plan-scoped candidate. The decision matrix selects a subset. If both marshal.json and the CSV are absent, defaults to the full canonical set.
- `--commit-and-push` (optional, default `true`): `true|false` — the resolved `commit_and_push` boolean from phase-5-execute config. When `false`, `push`, `pre-push-quality-gate`, and `pre-submission-self-review` are all removed from the candidate set by the `commit_push_disabled` pre-filter before the matrix runs (a local-only run).
- `--envelope-count` (optional, default `1`): Number of phase-5 `execution-context` envelopes the orchestrator should plan for. Persisted into the manifest's `phase_5.envelope_count`. When omitted, defaults to `1` (a single budget-bounded envelope greedily drives the task loop until the queue is empty or a TASK-boundary re-dispatch point fires). A non-positive value is clamped to `1`. The field is written under every decision-matrix rule (including `early_terminate`), so the `phase_5` block always carries it.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
file: execution.toon
created: true
manifest_version: 1
change_type_scope: settled
effective_change_type: bug_fix
settled_change_type: bug_fix
supplied_change_type: bug_fix
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
commit_push_dropped[0]:
pre_push_quality_gate_omitted: false
build_verdict_decision: build
decision_matrix_dropped[1]{step,reason}:
  ci-wait,"decide rule 'surgical_tech_debt' drops the legacy ci-wait step"
simplify_omitted: true
security_class_omitted[0]:
scope_gated_finalize_dropped[0]:
scope_gated_finalize_immune[0]:
unresolved_ask_provider_dropped[0]:
terminal_emission_dropped[0]:
ceremony_finalize_gates:
  self_review: auto
  qgate: auto
  simplify: auto
  security_audit: auto
ceremony_finalize_forced_in[0]:
ceremony_finalize_forced_out[0]:
execution_profile: full
lane_dropped[0]:
lane_warnings[0]:
```

Every field that can name more than one dropped step is a `{step, reason}` **record list**, not a boolean — `commit_push_dropped`, `decision_matrix_dropped`, `security_class_omitted`, `unresolved_ask_provider_dropped`, `lane_dropped`, and the two `scope_gated_finalize_*` lists. A boolean cannot say *which* step went or *why*, and each such field pairs with one `[STATUS]` `decision.log` line per record. **Not every multi-step field has reached that shape yet.** `ceremony_finalize_forced_out`, `scope_gated_finalize_dropped`, `scope_gated_finalize_immune`, and `unresolved_ask_provider_dropped` are still emitted as bare step-id lists: each reports *which* steps went but not *why*, and in some cases (`ceremony_finalize_forced_out`) a per-entry reason is available upstream and discarded by the compose-result projection. `terminal_emission_dropped` — the terminal-emission step dropped because the plan is not orchestrated — is a bare step-id list too, but by design rather than as a gap: its reason is fixed for every entry and rides the paired `[STATUS]` `decision.log` line, so a per-record copy would repeat one sentence per step. Treat `cmd_compose`'s return dict in [`scripts/manage-execution-manifest.py`](scripts/manage-execution-manifest.py) as the authority on each field's actual shape rather than inferring it from this paragraph. `pre_push_quality_gate_omitted` and `simplify_omitted` stay booleans because each names one fixed step; `build_verdict_decision` carries the build verdict verbatim (`build` / `not_necessary` / `unknown`) so an `unknown` verdict — which KEEPS the gate — is distinguishable from a `build` one. The full convention is normative in [`standards/decision-rules.md`](standards/decision-rules.md) § "Every subtraction is reported".

**change_type scope record.** `change_type_scope` names which scope drove every change-type-gated decision this compose made: `settled` when the plan's authoritative classification at `status.metadata.change_type` was present and used, or `supplied` when no settled classification existed and the caller-supplied `--plan-change-type` value stood alone. `effective_change_type` is the value actually consumed by the decision matrix and pre-filters; `settled_change_type` and `supplied_change_type` carry the two candidate inputs (either may be `null`/absent). This makes the narrowing auditable after the fact — a run can no longer disagree with itself about which change type narrowed the plan. A supplied value that contradicts a present settled classification never reaches this output: compose returns `change_type_scope_conflict` instead. See [decision-rules.md](standards/decision-rules.md) § "change_type scope reconciliation".

#### Compose-time step-resolution gate

As its final gate — after the frontmatter-order sort, over the FINAL emitted `phase_5.verification_steps` and `phase_6.steps` — `compose` resolves every emitted step id and **fails loud** on the first one that does not resolve. This closes the gap left by `validate-loadable`, which only checks built-in standards-file presence and short-circuits every external (`project:` / `bundle:skill`) step to `loadable: true`: a never-existed `bundle:skill` key, a renamed/removed `project:` skill, or a built-in doc deleted without sweeping `marshal.json` would otherwise compose silently and fail only much later at dispatch time.

Resolution is keyed on the step-id shape and the phase:

- **`project:`** step (either phase) resolves iff its project-local `{bare}/SKILL.md` exists under the repo root.
- **phase-5 canonical-verify** step (bare `{canonical}` or `verify:{canonical}`) resolves iff `{canonical}` is in the verify-canonicals universe — the composer's `_CANONICAL_TO_ROLE` keys unioned with every `ext-point-build-verify-step` implementor's declared `canonicals`.
- **phase-5 external `bundle:skill`** verify step resolves iff its (normalized) id is a discovered `ext-point-build-verify-step` implementor name.
- **phase-6 external `bundle:skill`** step resolves iff its (normalized) id is a discovered `ext-point-finalize-step` implementor name (the same `extension_discovery.find_implementors` query the finalize/verify seed and discovery surfaces use — the SOLE discovery path).
- **phase-6 built-in** step (bare / `default:`) keeps the existing standards/workflow file check.

On the first unresolvable id, `compose` returns `status: error`, `error: unresolvable_step`, and a `message` naming the offending step's **provenance** and the phase — plus `phase`, `step_id`, and `marshal_key` fields — and emits one `decision.log` line. The provenance distinguishes the two origins an emitted id can have: a **marshal.json-authored** step names the original `marshal.json` key (mapped back from the boundary-normalized emitted id via `marshal_phase_{5,6}_map`); a **phase-5 routed** step — one appended by the `execution_tier` COMMAND routing pass from a derived `verification.commands` entry, so absent from the marshal step map — is named as NOT authored in marshal.json but emitted by `architecture derive-verification`, so a reader traces it to the emitting build verb rather than a non-existent key. The gate never writes a partial manifest: the error returns before the step-params snapshot and `write_manifest`.

```toon
status: error
plan_id: EXAMPLE-PLAN
error: unresolvable_step
message: "phase_6 step `plan-marshall:ghost-review` in marshal.json is unresolvable: step `plan-marshall:ghost-review` is not a discovered ext-point-finalize-step implementor — the id resolves to no built-in finalize step, project-local skill, or bundle discovery-registry entry"
phase: phase_6
step_id: "plan-marshall:ghost-review"
marshal_key: "plan-marshall:ghost-review"
```

**Canonical-step-key assertion.** A sibling structural gate runs on the SAME FINAL emitted step lists, immediately after the resolution gate passes: every emitted `phase_5.verification_steps` and `phase_6.steps` id MUST be in **canonical form** — `canonicalize_step_key(step_id) == step_id`, i.e. no leading `default:` prefix and no promoted-alias (`PROMOTED_BUILTIN_STEP_IDS`) bundle spelling. Because the composer boundary-normalizes every candidate at intake, a non-canonical emitted id is a structural defect (a newly-introduced mis-keyed prefixed step that slipped past that normalization), so `compose` fails it loud rather than persisting a manifest whose keys would not reconcile with the record/assert step keys. On the first non-canonical id, `compose` returns `status: error`, `error: non_canonical_step`, naming the offending `step_id`, its `canonical` form, and the `phase`, and emits one `decision.log` line — and, like the `unresolvable_step` gate, never writes a partial manifest (it returns before the step-params snapshot and `write_manifest`). The assertion reuses D2's shared `canonicalize_step_key` resolver (`script-shared/scripts/_step_key_canonical.py`).

```toon
status: error
plan_id: EXAMPLE-PLAN
error: non_canonical_step
message: "phase_6 emitted step id `default:push` is not in canonical form (canonicalizes to `push`) — the id carries a `default:` prefix or a promoted-alias bundle spelling that the compose boundary normalization should have stripped"
phase: phase_6
step_id: "default:push"
canonical: push
```

### read

Read the manifest as TOON.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

**Output** (TOON): the full manifest content (see schema above), wrapped with `status: success` and echoed `plan_id`.

### lanes preview

Resolve all three execution-profile postures (`minimal` / `standard` / `full`) over the configured phase-6 candidate step list and return them — with per-posture step counts and summed token costs — in **one TOON**. This is the single projection the `phase-1-init` posture dialogue reads to show each posture's concrete kept-step set and cost preview. The lane contract (the closed `class` enum, the class→default-tier table, the resolution lattice) is owned by [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md).

**Preview/compose agreement contract.** The preview renders the same membership and the same ORDER `compose` reaches for every step whose fate marshal configuration alone decides, and names the steps whose fate it cannot know. It shares `_apply_unresolved_ask_provider_drop`, `_apply_lane_resolution`, and `_sort_steps_by_frontmatter_order` with `compose` — the sort included because `compose` sorts its final list, so an unsorted preview would report a different order for an identical membership. It cannot apply the remaining pre-filters, the six-row matrix, or `ceremony_finalize_selection`: those read PLAN inputs (`change_type` / `scope_estimate` / `track` / `affected_files_count` / `commit_and_push` / the live footprint) that do not exist at preview time. Rather than silently rendering a membership `compose` may not reach, the preview returns `plan_input_dependent_steps[]` naming the emitted steps still subject to such a decision — an empty list means preview and compose agree outright. See [standards/decision-rules.md](standards/decision-rules.md) § "Preview/Compose Agreement Contract".

`full` and `minimal` are pure config projections (the lane cutoff over the configured candidates); `standard` additionally drops every `full`-tier element. Each posture's `cost_sum_tokens` is `Σ(resolved element cost_size → cost_size_token_table)` (the six-size table, default `{XS:5K, S:25K, M:60K, L:130K, XL:260K, XXL:520K}`, overridable at `plan.phase-5-execute.cost_size_token_table`).

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
  standard:
    phase_6_steps[12]: [ ... ]
    phase_6_steps_count: 12
    cost_sum_tokens: 700000
  full:
    phase_6_steps[14]: [ ... ]
    phase_6_steps_count: 14
    cost_sum_tokens: 960000
plan_input_dependent_steps[2]: [ pre-submission-self-review, finalize-step-simplify ]
```

### record-step

Append one per-step execution record (outcome + token attribution) to the manifest's `execution_log[]` section. The manifest MUST already exist (composed by `phase-4-plan` Step 8b); `record-step` returns `file_not_found` otherwise.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  record-step \
  --plan-id {plan_id} \
  --step-id {step_id} \
  --phase {5-execute|6-finalize} \
  --outcome {executed|skipped|loop_back|failed|error} \
  [--total-tokens {N}] \
  [--tool-uses {N}] \
  [--duration-ms {N}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--step-id` (required): Step identifier being recorded (e.g., a phase-5 verification step ID or a phase-6 finalize step ID)
- `--phase` (required): `5-execute|6-finalize` — the phase the step ran in
- `--outcome` (required): `executed|skipped|loop_back|failed|error` — which of the five situations the row records. The four non-`executed` values do not overlap: `skipped` is a step that never ran, `loop_back` is a **productive non-completion** (the step examined its surface, filed findings and handed control back), `failed` is a step that ran cleanly and self-assessed not-clean, and `error` is a dispatch that raised, timed out, or was cut short. See [standards/manifest-schema.md](standards/manifest-schema.md) § "Which situation each `outcome` value means" — collapsing `loop_back` and `failed` into `error` is what made a thorough multi-round gate read as a defect.
- `--total-tokens` (optional, **no default**): Total tokens attributed to the step
- `--tool-uses` (optional, **no default**): Tool-use count attributed to the step
- `--duration-ms` (optional, **no default**): Wall-clock duration in milliseconds

**Absence is not zero for the three token columns.** Each of the three flags is three-state and has NO `0` default. Pass a value — including `0` — only when that is what you MEASURED: a `skipped` step really did consume nothing, so `--total-tokens 0` is its correct record. **Omit the flag entirely when nothing was measured** (an inline step with no `<usage>` envelope to forward), and the row records the literal `unmeasured` instead. Passing `0` for an unmeasured column is the prohibited move: it is byte-identical to a measured zero, and no reader can recover the difference afterwards. The absence-vs-zero contract is a property of the ledger FAMILY — `manage-metrics` publishes the same rule and the same literal for its dispatch-boundary row — and the two definitions are mirrors held in lock-step by a contract-drift test on each side. See [standards/manifest-schema.md](standards/manifest-schema.md) § "`execution_log[]` — the per-step execution log".

Each call appends exactly one row to `execution_log[]` (an ordered append log, not a keyed map) and emits one `decision.log` line via the in-process `_emit_decision_log` helper. Re-invocation appends another row deterministically, so every dispatch of a step is recorded. This makes per-step execution metadata loggable per-plan deterministically rather than relying on the fragile orchestrator `<usage>`-forwarding boundary call.

**Canonical step-key contract.** `--step-id` is routed through the single shared resolver `canonicalize_step_key` (`script-shared/scripts/_step_key_canonical.py`) before the `execution_log[]` row is appended — the same resolver `manage-status`'s `mark-step-done` / `assert-step-recorded` and every manifest-bundle boundary-normalization call site consume. It maps a promoted built-in-equivalent bundle id via `PROMOTED_BUILTIN_STEP_IDS` (`plan-marshall:automatic-review` → `automatic-review`), strips a leading `default:` prefix, and preserves `project:` / other `bundle:skill` ids verbatim (idempotent on already-canonical input). Recording under the canonical key guarantees execution-log keys reconcile with the manifest `phase_steps` / phase-step-list keys: the record, assert, and manifest `step_id` all agree, so a bare↔`default:` / promoted-alias variant is a canonical MATCH rather than a tolerated `step_record_mismatched_key` near-miss, and a genuine mismatch still fails loud.

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

### refire-report

Report per-step firing / re-fire counts derived from the `execution_log[]` rows `record-step` already appends. Read-only — it writes nothing and emits no decision-log line.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  refire-report \
  --plan-id {plan_id} \
  [--phase {5-execute|6-finalize}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase` (optional, default all phases): Restrict the derivation to one phase

Because `execution_log[]` is an ordered append log with one row per firing, a step's re-fire count is `max(0, firings - 1)`: the first `executed` row is the firing the pipeline owes, and every later one is an **extra** firing. Rows are sorted by descending `refires`, then by `step_id`, so the worst offender reads first.

**`refires` counts extra firings, NOT re-stales.** At least four mechanisms produce a second `executed` row — the dispatcher's HEAD-advance re-entry check re-firing a re-staled verdict, a `loop_back` record re-firing the step on the next entry, a retry after a `failed` record, and the `push` barrier's parity-driven re-fire plus its explicit post-PR re-invocation — and this column does not separate them. A before/after comparison over the same plan shape stays sound, since the other causes are common to both arms; a single run's `refires` is not a re-stale count and must not be reported as one. The consuming model — what advances HEAD, what a re-stale costs, and how an advance is classified as invalidating or not — is owned by [`phase-6-finalize/standards/verdict-currency.md`](../phase-6-finalize/standards/verdict-currency.md).

**Two coverage boundaries the payload names rather than hides.** A `skipped` row is counted in its own column and never folded into `firings` — a skip is precisely what a preserved verdict produces, so folding it in would make the instrument unable to measure the thing it exists to measure. And `total_tokens` is a **floor**: `record-step` receives the `<usage>` triple only for steps dispatched as Task agents, while an inline step's caller omits the flags (recorded as the `unmeasured` token, never a fabricated zero), so `token_population` states which rows the figure was summed over. A saving computed from this column is reported with that floor attached, never as a measured total.

**The floor is SIZED, not merely asserted.** Every step row and the `totals` block carry `unmeasured_columns` and `unrecognised_columns` — the count of three-state cells the sum could not read. Without them an all-unmeasured population and a genuinely-zero one are the same number, which is the confident-but-untrue signal the column state exists to remove.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
phase: 6-finalize
execution_log_rows: 11
steps[2]{step_id,firings,refires,skipped,errors,total_tokens,tool_uses,duration_ms,unmeasured_columns,unrecognised_columns}:
  pre-submission-self-review,7,6,0,0,412000,58,930000,0,0
  push,1,0,3,0,0,0,0,3,0
totals: { steps: 2, firings: 8, refires: 6, skipped: 3, errors: 0, unmeasured_columns: 3, ... }
token_population: record-step rows only; ...
```

On a missing manifest: `status: error`, `error: file_not_found`. On an invalid `--phase` value: `status: error`, `error: invalid_phase`.

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

### reconcile

Reconcile the frozen `phase_6.steps` against **live** configuration at finalize entry. This is the verb that keeps a write-time snapshot from silently diverging from the configuration it was composed against — including divergence caused by the plan's own edits.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  reconcile --plan-id {plan_id} [--apply]
```

**Parameters**:

- `--plan-id` (required): Plan identifier
- `--apply` (optional): Write the reconciled list back to `execution.toon`. Without it the verb is a pure report and mutates nothing.

**The fail-direction split.** A self-modifying plan deletes a finalize step's standards doc and sweeps `marshal.json`, and its own already-frozen manifest still names the step. `validate-loadable` (§ below) hard-aborts on any unloadable step, which blocks exactly that legitimate work. `reconcile` splits the case `validate-loadable` conflates, and the split is the whole point:

| Frozen step | Live candidate set | Verdict | Action |
|---|---|---|---|
| unloadable | **absent** from it | `stale` | **Drop.** Live config agrees the step is gone, so the frozen view is merely behind a change this plan already made. |
| unloadable | **still lists it** | `broken` | **Fail loud** (`unreconcilable_step`, canonical actionable message). The doc was deleted without sweeping `marshal.json` — the original motivating failure. Reconciling it away would silently drop work the project still schedules. |
| loadable | — | retained | Untouched. |

**Backfill is narrow by construction.** Only a live candidate absent from `phase_6.candidate_steps` is owed — such a step never faced the decision matrix. A candidate the matrix saw and dropped must stay dropped, so "in live config but not in the manifest" is NOT the backfill test. When `candidate_steps` is absent (a manifest frozen before the field existed) or live config is unreadable, the verb reports `backfill_determinable: false` and backfills nothing; guessing would resurrect every matrix-dropped step. The drop direction needs no snapshot and still runs.

**Fail closed on unreadable live config.** When the live candidate set cannot be read at all (`candidate_source: unavailable`), "config dropped it" is indistinguishable from "config still wants it", so every unloadable step is classified `broken` — today's hard fail — rather than reconciled away on absent evidence.

On `--apply` the merged list is re-sorted through the shared `_sort_steps_by_frontmatter_order` choke point (the same one `compose` uses), the dropped steps' `step_params` entries are pruned, and backfilled steps get a params snapshot from the live marshal map. One `decision.log` line is emitted per dropped and per backfilled step, so every subtraction and addition is auditable.

**Output** (TOON):

```toon
status: success
plan_id: EXAMPLE-PLAN
file: execution.toon
reconciled: true
applied: true
stale[1]: [ retired-step ]
broken[0]:
backfill[1]: [ newly-added-step ]
backfill_determinable: true
candidate_source: marshal.json
steps_count: 12
```

On a broken step: `status: error`, `error: unreconcilable_step`, plus `message` (canonical phrasing), `broken[]`, `stale[]`, and `candidate_source`. No manifest is written on that path.

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
2. **Not re-resolved at read time.** `read` is a literal file load. `phase-5-execute` and `phase-6-finalize` consume `phase_5.verification_steps` and `phase_6.steps` verbatim from the persisted file — they do NOT re-derive the list from current decision rules, do NOT re-consult `marshal.json` for fresh candidate sets, and do NOT re-apply the decision matrix at consumption time. The manifest IS the contract for the running plan. (The one bounded exception is the explicit `reconcile` verb — see below. It is an entry-point call, not a resolution the readers perform, so this item holds for every read path.)

**Consequence — `Phase 6` reads the pre-change snapshot**: a plan that modifies a decision rule, a `marshal.json` default, the six-row decision matrix, or any other manifest-composer input still sees the **pre-change** manifest shape when `phase-6-finalize` reads it back, even after `/sync-plugin-cache` has run and the Claude Code session has been restarted. The cache sync and session restart fix the manifest's **future composition** (subsequent plans that invoke `compose`), not the current plan's already-written `execution.toon`.

**`reconcile` is the bounded exception, and it does not weaken either half.** At finalize entry `reconcile` is the ONE operation that reads live `marshal.json` and may amend the persisted list — but only in the two directions a frozen view can be provably wrong: a step whose standards doc is gone *and* which live config no longer lists (dropped), and a candidate that entered live config *after* this manifest recorded its `phase_6.candidate_steps` (backfilled). It never re-runs the decision matrix, never re-derives the list from current rules, and never re-adds a candidate the matrix already dropped. Read-time consumption stays verbatim: `reconcile` is an explicit entry-point verb, not a resolution the readers perform.

Meta-projects that author marketplace bundles maintain their own self-host fence to guard against this class of staleness in their own finalize phase; consumer projects of plan-marshall do not encounter the failure mode because their plans do not modify the manifest composer's own resolution roots. Plans that intend to use a newly-introduced step or a newly-changed decision rule in their own finalize phase MUST either (a) re-run `compose` after the cache sync and session restart (re-composition re-reads the now-current cache state) or (b) edit `execution.toon` directly with the intended step list. The `validate`, `validate-loadable`, and `reconcile` operations remain valid post-edit; none of the three re-derives the selection. `validate` and `validate-loadable` read the persisted file alone; `reconcile` reads it and additionally consults live `marshal.json`, which is exactly what lets it diff a hand-edited list against current configuration.

The write-time-snapshot model is a deliberate design choice — it makes the manifest diffable, auditable, and resumable across crashes. Re-resolving at read time would couple every Phase 6 step dispatch to the in-memory decision rules, which is precisely the coupling the manifest exists to break — and is why `reconcile` heals a provably-stale entry rather than recomputing the selection.

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
message: "step `missing-step` is missing standards file `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/missing-step.md` — the plan likely deleted the file without sweeping `marshal.json`"
```

**Output (bulk form)**: a `results[N]` table with one row per manifest step plus an `unloadable_count` summary, e.g.:
```toon
status: success
plan_id: EXAMPLE-PLAN
unloadable_count: 1
results[3]{step_id,standards_path,loadable,message}:
  push,marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md,true,
  create-pr,marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md,true,
  ghost-step,marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ghost-step.md,false,"step `ghost-step` is missing standards file `…ghost-step.md` — the plan likely deleted the file without sweeping `marshal.json`"
```

The bulk form requires the manifest to exist on disk; if it does not, the script returns the standard `file_not_found` error.

---

## Scripts

**Script**: `plan-marshall:manage-execution-manifest:manage-execution-manifest`

| Command | Parameters | Description |
|---------|------------|-------------|
| `compose` | `--plan-id --plan-change-type --track --scope-estimate [--recipe-key] [--affected-files-count] [--phase-5-steps] [--phase-6-steps] [--commit-and-push] [--envelope-count]` | Compose and write execution.toon (`--phase-5-steps`/`--phase-6-steps` are fallback-only — `marshal.json` is the authoritative candidate source; `--plan-change-type` is reconciled against the settled `status.metadata.change_type`) |
| `read` | `--plan-id` | Read manifest as TOON |
| `lanes preview` | `--plan-id [--phase-6-steps]` | Resolve the minimal/standard/full phase-6 step sets + cost sums in one TOON (the posture-dialogue projection) |
| `record-step` | `--plan-id --step-id --phase {5-execute\|6-finalize} --outcome {executed\|skipped\|error} [--total-tokens] [--tool-uses] [--duration-ms]` | Append a per-step execution-log row (outcome + token attribution) to execution.toon |
| `refire-report` | `--plan-id [--phase {5-execute\|6-finalize}]` | Report per-step firing / re-fire counts derived from the existing `execution_log[]` rows (read-only; names its token-population floor) |
| `step-params get` | `--plan-id --phase {5-execute\|6-finalize} --step-id` | Return a step's snapshotted param object from the manifest (plan-local read) |
| `step-params set` | `--plan-id --phase {5-execute\|6-finalize} --step-id --param --value` | Write a per-plan param override into the manifest snapshot |
| `reconcile` | `--plan-id [--apply]` | Reconcile the frozen `phase_6.steps` against live marshal.json config — drop steps live config also dropped, fail loud on a step live config still wants but whose doc is gone, backfill only candidates new since compose |
| `validate` | `--plan-id [--phase-5-steps] [--phase-6-steps]` | Validate manifest schema + step IDs against the caller-supplied allow-list CSVs (a separate surface from compose's candidate source) |
| `validate-loadable` | `--plan-id (--step-id ID \| --all)` | Verify standards file presence for built-in `phase_6.steps` entries |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `file_not_found` | execution.toon doesn't exist (read/validate) |
| `invalid_change_type` | --plan-change-type not in the valid enum |
| `change_type_scope_conflict` | `compose` — the supplied `--plan-change-type` (a DELIVERABLE-scoped value) contradicts the plan's settled classification at `status.metadata.change_type` (the PLAN scope). Fail-loud; names BOTH values (`settled_change_type`, `supplied_change_type`); writes no manifest. A plan with NO settled classification never trips this — the supplied value stands alone |
| `invalid_scope_estimate` | --scope-estimate not in the valid enum |
| `invalid_track` | --track not `simple` or `complex` |
| `invalid_phase` | `record-step` --phase not `5-execute` or `6-finalize` |
| `invalid_outcome` | `record-step` --outcome not `executed`, `skipped`, or `error` |
| `invalid_manifest` | Manifest schema invalid or step IDs unknown; or `step-params set` target section malformed |
| `unresolvable_step` | `compose` — a FINAL emitted phase-5/6 step id resolves to no built-in doc, project-local skill, or bundle discovery-registry entry (fail-loud; names the offending step's provenance — the `marshal.json` key for an authored step, or the derive-verification routing origin for a routed phase-5 step — and phase) |
| `phase_6_order_violation` | `compose` — the FINAL composed `phase_6.steps` is not verifiably in ascending frontmatter `order`: either an `order_inversion` (a step precedes one with a lower `order`) or an `unresolvable_order` (a built-in / `project:` step whose `order` does not resolve, so its pinned position cannot be verified). Fail-loud; names the offending `step_id`, the `reason`, and `phase`; writes no partial manifest |
| `non_canonical_step` | `compose` — a FINAL emitted phase-5/6 step id is not in canonical form (`canonicalize_step_key(step_id) != step_id`; a `default:` prefix or promoted-alias bundle spelling slipped past intake normalization). Fail-loud; names the offending `step_id`, its `canonical` form, and phase; writes no partial manifest |
| `unreconcilable_step` | `reconcile` — a frozen `phase_6.steps` entry has no loadable standards doc AND live `marshal.json` still lists it (or live config is unreadable, so the drop cannot be substantiated). Fail-loud; names the offending step in `broken[]` and carries the canonical actionable message; writes no manifest |
| `invalid_arguments` | `validate-loadable` invoked without exactly one of `--step-id` / `--all` |
| `step_not_found` | `step-params get`/`set` `--step-id` has no snapshotted params in the manifest for the given phase |

---

## Canonical invocations

The canonical argparse surface for `manage-execution-manifest.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section. Consuming skills xref this
section by name (e.g., "see `manage-execution-manifest` Canonical invocations →
`compose`") instead of restating the command inline.

### compose

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest compose \
  --plan-id PLAN_ID \
  --plan-change-type {analysis|feature|enhancement|bug_fix|tech_debt|verification} \
  --track {simple|complex} \
  --scope-estimate {none|surgical|single_module|multi_module|broad} \
  [--recipe-key KEY] [--affected-files-count N] \
  [--phase-5-steps LIST] [--phase-6-steps LIST] \
  [--commit-and-push {true|false}] [--envelope-count N]
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
  --outcome {executed|skipped|loop_back|failed|error} \
  [--total-tokens N] [--tool-uses N] [--duration-ms N]
```

The three token flags are optional **and have no `0` default** — omit them when nothing was measured and the row records the `unmeasured` token; pass a value, `0` included, only when that is what was measured.

### refire-report

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest refire-report \
  --plan-id PLAN_ID \
  [--phase {5-execute|6-finalize}]
```

Read-only over the `execution_log[]` rows `record-step` appends — it writes nothing and emits no decision-log line. Omitting `--phase` covers every phase.

### validate

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest validate \
  --plan-id PLAN_ID \
  [--phase-5-steps LIST] [--phase-6-steps LIST]
```

On `validate` the `--phase-5-steps` / `--phase-6-steps` CSVs are the **caller-supplied allow-list** of permitted step IDs — a separate input from `compose`'s candidate source (where the same-named flags are fallback-only against the marshal-authoritative seeding above). Omitting a flag skips that phase's step-ID check; when supplied, every manifest step ID must appear in the allow-list (prefix-agnostic on `default:`; `project:` / `bundle:skill` prefixes compare verbatim) or validation fails with `invalid_manifest`. Because `compose`'s `execution_tier` routing can append `verify:{verb}` step IDs that were never in the configured candidate list, the allow-list must also cover the compose-routed `verify:{verb}` IDs.

### reconcile

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest reconcile \
  --plan-id PLAN_ID [--apply]
```

Without `--apply` the verb reports the divergence and writes nothing. With `--apply` it persists the reconciled `phase_6.steps`. It never writes on the `unreconcilable_step` error path.

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

The six-row decision matrix is documented in [standards/decision-rules.md](standards/decision-rules.md). The matrix maps the inputs (`change_type`, `track`, `scope_estimate`, `recipe_key`, `affected_files_count`) to:

- `phase_5.early_terminate` (true/false)
- The subset of `phase_5.verification_steps` chosen from the candidate set
- The subset of `phase_6.steps` chosen from the candidate set

For each rule fired, `compose` emits one `decision.log` entry — written in-process via `plan_logging.log_entry` (NOT by shelling back out to the executor) — with the canonical prefix `(plan-marshall:manage-execution-manifest:compose)` and the rule name. The in-process write resolves the plan dir the same way the manifest write does, so the line always lands in the plan's own `logs/decision.log`; the prior executor-subprocess path silently dropped every line because the composer runs from the plugin cache, outside the project tree where `.plan/execute-script.py` lives. This satisfies the request example "one entry per decision".

### Scope-gated phase-6 filtering (`scope_gated_finalize`)

Before the six-row matrix, the composer applies a scope-gated pre-filter that drops heavyweight phase-6 review/audit steps based on `scope_estimate`:

- **`surgical`** — drops `plan-marshall:plan-retrospective`, pre-submission-self-review, and `project:finalize-step-plugin-doctor`. Every bare and prefixed form is matched: for pre-submission-self-review this covers the built-in `default:pre-submission-self-review` (normalized to bare `pre-submission-self-review` at intake). The candidate list is `default:`-namespace-normalized at intake, but `project:` / `bundle:skill` prefixes are preserved verbatim — so `plan-marshall:plan-retrospective` and `project:finalize-step-plugin-doctor` are matched by their full prefixed form, not a bare normalization.
- **`single_module`** — drops only `plan-marshall:plan-retrospective`.
- **`multi_module` / `broad` / `none`** — no implicit subtraction; the full candidate set is retained.

**Declared-lane immunity** — membership in a drop set is not sufficient to drop. A step declaring an explicit non-`standard` per-element `lane` override is immune and is kept whatever the `scope_estimate` says. The declaration is resolved from the MERGED source `_read_merged_phase_6_step_map(plan_id)`, which overlays the plan-local `status.metadata.finalize_step_overrides` map onto the project-wide `marshal.json::plan.phase-6-finalize.steps` map — plan-local wins per step key, merged per knob — so an operator's answer captured for one plan grants immunity exactly as a project-wide declaration does. Both channels, their shared shape and enum, and the full precedence ordering are the contract-of-record in [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md) § "Per-element override knob"; the enum is not restated here. The same merged map feeds the peer reader behind the four ceremony gates, so the two readers of this one field can never disagree. This gate is IMPLICIT (it infers intent from the scope estimate) while a `lane` override is the operator stating what they want, and an implicit inference must not silently override an explicit declaration. The immunity is load-bearing because the pre-filter runs BEFORE ceremony selection and lane resolution, and the ceremony `always` re-add path covers only the four ceremony gates — so for any other step (canonically `plan-marshall:plan-retrospective`) a drop here makes the declared lane structurally unreachable rather than merely outvoted. `automatic-review` therefore needs no carve-out of its own: the general rule already keeps it governed purely by its configured `lane` and lane tier.

The composer emits one `decision.log` line per scope-gated subtraction (canonical prefix `(plan-marshall:manage-execution-manifest:compose) scope_gated_finalize subtraction`) and one per immunity retention (`… scope_gated_finalize immunity`), and surfaces `scope_gated_finalize_dropped` and `scope_gated_finalize_immune` in the `compose` result for observability — a retention is made as visible as a subtraction, since a step surviving a gate that names it is otherwise indistinguishable from a gate that never ran.

### Generic footprint pre-filter for canonical-verify steps (`canonical_verify_inactive`)

After the six-row matrix and `execution_tier` routing produce the final `phase_5.verification_steps` list, the composer applies a canonical-agnostic footprint pre-filter: a `default:verify:{canonical}` step whose derived role is a footprint-gated whole-tree role (`integration` / `e2e`) is dropped when the live footprint is non-empty AND carries no path of that role. The core roles (`quality-gate` / `module-tests` / `coverage`) are never footprint-gated. The pre-filter is a no-op when the footprint is unresolvable (early compose, before the worktree is materialized) or resolvable-but-empty, so every canonical survives until a re-compose can observe a real footprint. The composer emits one `decision.log` line when at least one step is dropped (canonical prefix `(plan-marshall:manage-execution-manifest:compose) canonical_verify_inactive`). The full rule and the safety-against-compose-time-emptiness rationale are documented in [standards/decision-rules.md](standards/decision-rules.md) § "Generic footprint pre-filter".

### Command-level execution_tier routing (`execution_tier_routing`)

Before the per-step stamping below, the composer walks every task's `verification.commands` and routes each build command by its resolved `execution_tier` (see [standards/decision-rules.md](standards/decision-rules.md) § "execution_tier Routing" for the full predicate). For `orchestrator`-tier commands the verb maps to a bare phase-5 step ID: the four canonical verbs route through the `_VERB_TO_PHASE_5_STEP` fast path (`quality-gate` / `verify` / `module-tests` / `coverage`), and every other parseable verb generalizes to the bare `verify:{verb}` step and routes to it — the command is removed from the task, so no leaf runs it inline. (A custom / unknown verb whose `verify:{verb}` is unresolvable still routes here, then fails loud at the compose-time resolution gate; only the two kinds named below are kept with the task instead.) Each non-canonical routed verb is named in its own `decision.log` line (canonical prefix `(plan-marshall:manage-execution-manifest:compose) execution_tier routing`), in addition to the summary line carrying `mutated_tasks` and the final step list.

**Two kinds of orchestrator-tier command are kept with the task instead of routing** — both stay in the task's `verification.commands` so the mismatch stays observable at the next compose, rather than being silently dropped or routed to a step that fails compose:

- **Raw-shell / non-build**: only commands in the canonical Bucket B build shape (`python3 .plan/execute-script.py plan-marshall:build-*:... run --command-args "..."`) carry a parseable verb. A raw-shell or non-`plan-marshall:build-` command that the tier classifier nonetheless labels `orchestrator` cannot be verb-routed and is left in the task.
- **Build-phase-canonical carve-out**: `derive-verification` legitimately emits `compile` and `test-compile` — known canonical build commands with no phase-5 verify gate. Routing either to `verify:compile` / `verify:test-compile` would append an unresolvable step and fail the whole compose (`unresolvable_step`), so the routing pass keeps such a command with the task (the per_task fallback the leaf re-resolves live). The carve-out is restricted to KNOWN canonical commands (the vocabulary registry) so a genuinely custom / typo'd verb still routes and fails loud.

**Interaction with per-step stamping**: routing runs first and may append `verify:{verb}` entries to `phase_5.verification_steps`; the stamping pass below then resolves a tier for the FINAL list, so every routed step — canonical or generalized — receives a stamped `{step_id, tier}` record. A generalized `verify:{verb}` whose canonical is unresolvable stamps to the `per_task` permissive default per the stamping rule.

### Per-step execution_tier stamping (`step_execution_tier`)

After the canonical-verify footprint pre-filter produces the FINAL `phase_5.verification_steps` list, the composer resolves each selected step's `execution_tier` and stamps a `phase_5.step_execution_tier` record list (one `{step_id, tier}` object per verification step). Each built-in canonical-verify step (`verify:{canonical}`) is resolved via a whole-tree `architecture resolve --command {canonical}`, reading the `execution_tier` field the resolve TOON emits; every other step id (an external `project:` / `bundle:skill` step, or a `verify:{canonical}` whose canonical is unresolvable) defaults to `per_task`. The list is total over `verification_steps` — the composer never emits an unresolved tier.

**The stamp is ADVISORY, not the routing authority.** The tier derives from two run-config quantities `manage-architecture` reads — whether the command key has been **measured at all**, and the **adaptive learned build duration** behind `bash_timeout_seconds` — and every intervening build updates both. An unmeasured step stamps `orchestrator` by the fail-closed rule and re-stamps `per_task` after its first observed run, and a step whose learned duration sits near the 600s Bash ceiling crosses the ceiling between compose and execute in ordinary operation, so a compose-time snapshot cannot be a durable routing fact. The routing authority is the **live `architecture resolve` the leaf performs when it runs the step** (see [`../phase-5-execute/standards/canonical_verify.md`](../phase-5-execute/standards/canonical_verify.md) § Workflow steps 1-2); the stamp serves planning and observability — it tells the orchestrator how many orchestrator-tier steps to expect. Consistent with that, `per_task` is the **permissive default, not a safe floor**: it is the value that would put a long build inline where the host platform auto-backgrounds it and a leaf cannot reap it, and it is acceptable only because the live re-resolve is what actually routes.

The leaf-no-background-build invariant itself is unchanged — `phase-5-execute` runs only `per_task`-tier steps inline and routes every `orchestrator`-tier step to the main-context orchestrator's `await-long-running` detach-and-notify seam, the only component permitted to background a build — but it is the LIVE tier that enforces it, not the manifest stamp. The composer emits one `decision.log` line naming each step's compose-time tier (canonical prefix `(plan-marshall:manage-execution-manifest:compose) step_execution_tier stamping`) and surfaces `step_execution_tier` in the `compose` result. The full rule is documented in [standards/decision-rules.md](standards/decision-rules.md) § "execution_tier Stamping" and the leaf-boundary contract in [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md) § "Leaf cannot reap a backgrounded build".

### phase-6-finalize ceremony-gate selection (`ceremony_finalize_selection`)

After the six-row matrix produces the final `phase_6.steps` (and after `execution_tier` routing), and before the execution-profile lane resolution, the composer applies the four `plan.phase-6-finalize` ceremony gates to force their finalize steps in or out. Each gate's run decision is derived from its owning finalize step's per-element `lane` override (`off→never`, `minimal→always`, `standard`/absent→`auto`):

| Gate | Owning step (its `lane` override) | `never` → drop · `always` → force-include · `auto` → defer |
|------|-----------------------------------|------------------------------------------------------------|
| `self_review` | `default:pre-submission-self-review` | force the pre-submission structural + cognitive self-review |
| `qgate` | `default:pre-push-quality-gate` | force the finalize blocking-findings re-capture |
| `simplify` | `default:finalize-step-simplify` | force the holistic post-implementation simplification sweep |
| `security_audit` | `default:finalize-step-security-audit` | force the proactive security sweep |

`always` is the only path that re-adds a step the relevant pre-filter dropped — an operator-set `always` (via `lane: minimal`) overrides the implicit gate. All four gates now ride the same per-element `lane` override channel: each gate's decision is derived from `steps[<owner>].lane` (via `_read_finalize_gates`), with no flat phase-level `qgate` sibling and no step-owned run-at-all param. The transform NEVER touches `automatic-review` — its gate map contains only the four ceremony steps, so `automatic-review` remains governed purely by its own `lane` through the execution-profile lane-resolution pass, with no separate force-add guard.

The composer emits one `decision.log` line per forced change (canonical prefix `(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection`) and surfaces `ceremony_finalize_gates`, `ceremony_finalize_forced_in`, and `ceremony_finalize_forced_out` in the `compose` result for observability. The full rule (gate→step map, `automatic-review` carve-out, post-matrix-transform rationale) is documented in [standards/decision-rules.md](standards/decision-rules.md) § "plan.phase-6-finalize Selection". The per-element `lane` override schema is owned by [`manage-config/standards/data-model.md`](../manage-config/standards/data-model.md) § phase-6-finalize and [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md).

### Execution-profile lane resolution (`lane_resolution`)

After the change-type / scope pre-filters and `ceremony_finalize_selection` produce the `phase_6.steps` list, and **before** the frontmatter-order sort, the composer applies the execution-profile lane cutoff. The posture is read from `status.metadata.execution_profile` (absent → `full` → no pruning, preserving the pre-lane composition path for every plan that never chose a posture). Each lane-participating element self-declares a `lane:` frontmatter block (`class` / `tier` / `prunable_when` / `cost_size`); the closed enums and the class→default-tier table are owned by [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md). Per element the composer resolves the effective tier (per-element `marshal.json` `lane` override ▸ declared `lane.tier` ▸ class default) and keeps the element iff `effective_tier ⊑ posture` on `minimal ⊏ standard ⊏ full`:

- `minimal` keeps only the tier-`minimal` floor (`core` / `derived-state` plus the `minimal`-deviated lessons steps);
- `standard` additionally keeps tier-`standard` elements and drops tier-`full` ones (`security-audit`, `plan-retrospective`);
- `full` keeps everything (a no-op).

An element with no `lane:` block is not lane-participating and is always kept. A weakening `off` override of a `derived-state` / `core` floor element is **immune — the `off` is ignored and the element stays kept at its class-default tier** (§5 of the lane-selection design — `minimal` must never drop required derived state; a weakening `off` on a mandatory floor element cannot disable it, and the composer surfaces an informational note recording the neutralization). `automatic-review` participates in this pass like any other adversarial lane element — its keep/drop is governed purely by its configured `lane` and lane tier, with no separate downstream force-add guard, so a `minimal` posture or an `off` override that drops it is honored as the operator's decision (adversarial elements keep honoring `off` as a real opt-out). The q-gate is never a phase-6 finalize step, so it is never lane-pruned. The composer emits one `decision.log` line when at least one step is dropped (canonical prefix `(plan-marshall:manage-execution-manifest:compose) lane_resolution`), one line per lane warning (including the immune-`off` informational note), and surfaces `execution_profile`, `lane_dropped`, and `lane_warnings` in the `compose` result. `lane_warnings` has **two producers**: the lane resolution itself (the immune-`off` neutralization note) and the **ceremony pre-filter** — when the `simplify_inactive` / `security_class_inactive` pre-filter drops a step that the operator's selected posture/lane would have included (and the ceremony `always` gate did not force it back in), the composer appends a `{step, warning}` entry naming the ceremony pre-filter, not the lane, as the remover, so the drop is never silent. The per-pre-filter result fields sit alongside it: `simplify_omitted` stays a boolean, while the security leg reports `security_class_omitted` — a list of `{step, reason}` records, one per dropped security-class step — because its population is metadata-derived and a bare boolean could name neither the step nor the reason. The full rule is documented in [standards/decision-rules.md](standards/decision-rules.md) § "Execution-profile lane resolution".

**Twice-compose timing.** `compose` runs twice (lane design §4.5): once at **init** (`phase-1-init`, provisional `standard` footprint prunes) and once at **end-of-phase-4** (idempotent re-compose with firm signals). The posture and the `minimal`/`full` shapes are fixed at init and never change on the second call; only `standard`'s footprint-gated prunes can move (in the safe, more-validation direction), and that refinement is **logged, never re-prompted**.

### Frontmatter-order sort (`frontmatter_order_sort`)

After the execution-profile lane resolution (the last transform to add or drop a step) and before manifest persistence, the composer reorders the final `phase_6.steps` into ascending frontmatter `order` via `_sort_steps_by_frontmatter_order` (`_manifest_validation.py`). The stable sort reorders every order-resolvable step while entries whose `_resolve_step_order` is `None` (external `bundle:skill` steps, non-string entries) keep their original index, so `archive-plan` (terminus order 1100) is the terminal barrier regardless of the marshal.json seed order — the single choke-point correcting the sync-defaults append misordering and any other upstream seed corruption. It is also the sole ordering authority for `automatic-review` (order 30, sorted before the plan-mutating tail), so no separate placement validator is required. The transform is unconditional and emits no dedicated `decision.log` line. The full rule (pin semantics, barrier consequence, insertion-helper interaction) is documented in [standards/decision-rules.md](standards/decision-rules.md) § "Frontmatter-Order Sort".

### Post-compose ascending-order gate (`phase_6_order_violation`)

`check_emitted_steps_ascending_order` asserts over the FINAL `phase_6.steps` that the sort actually held, and fails the compose loud otherwise — the assertion half of "the composer sorts so the barrier invariant holds, the validator asserts the sort held". It rejects two shapes: an `order_inversion` (a step whose resolved `order` is less than the maximum seen at a preceding position — the message names both steps of the pair) and an `unresolvable_order` (a built-in or `project:` step whose `order` does not resolve, because its source declares no integer `order:` key or its source file could not be resolved).

Treating an unresolvable order as an offence rather than a skip is the point of the gate. The sort PINS an order-unresolvable entry at its original index, and the seed-path `_check_ascending_order` SKIPS exactly such an entry — so before this gate, a step that should carry an order but whose source could not be read was pinned wherever the seed put it and then went unchecked, letting a source-mutating step land after the merge gate with a green compose. A `bundle:skill` external step is orderless by design and is still skipped without complaint.

Backing this, `_resolve_step_order_verdict` distinguishes `resolved` / `not_declared` / `source_unresolvable` / `not_applicable`; `_resolve_step_order` remains the order-only projection the sort and the seed check consume. The gate runs AFTER the `unresolvable_step` / `non_canonical_step` gates so a missing source file is reported as the resolution defect it is, leaving this gate the case those cannot see — a source that resolves but declares no readable `order:`. It asserts the COMPOSED list, while `validate-loadable --check-seed` asserts the pre-composition seed; neither disturbs the array-authority contract on `validate-loadable --all`. Like its sibling gates it returns before the step-params snapshot and `write_manifest`, so a failing compose never writes a partial manifest. The full rule is documented in [standards/decision-rules.md](standards/decision-rules.md) § "Post-Compose Assertion: `phase_6_order_violation`".

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
