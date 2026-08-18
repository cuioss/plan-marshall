# Run report — 340-token-ledgers-disagree-and-the-smallest-is-named-actual (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/token-ledgers-disagree-q3t771` (harness-assigned)
**PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded by bundle path (the `plan-marshall` plugin is not installed in this cloud session, so
`Skill: {bundle}:{skill}` notation was not used):

| Skill | Route |
|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md` |
| `plan-marshall:persona-implementer` | production code (work identity) |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

No skill was unobtainable by both routes.

## D1 — the hard gate

**Arithmetic re-derivation: BLOCKED, as the plan anticipated.** The three ledgers' artifacts live under
`.plan/local/plans/{plan_id}/`, which is git-ignored and absent from this clone. Per D1's corpus-reachability
clause the run did not search for them and derived the **writer-side** answer instead. Every claim below is
re-derived from source in this clone, with file and symbol.

### The three ledgers, and their populations by construction

| Ledger | Writer | Population it can hold |
|---|---|---|
| `execution.toon` → `execution_log[]` | `manage-execution-manifest/scripts/manage-execution-manifest.py:2600` `cmd_record_step` | **2 of 6 phases.** `VALID_RECORD_PHASES = ('5-execute', '6-finalize')` (`_manifest_core.py:247`), enforced by a hard `invalid_phase` refusal at `manage-execution-manifest.py:2618`. |
| `work/metrics.toon` phase rows | `manage-metrics/scripts/manage-metrics.py:975` `_close_phase_accumulating` (via `end-phase` / `phase-boundary`) | **6 of 6 phases.** Gated on `PHASE_NAMES = list(PHASES)`, i.e. `1-init … 6-finalize` (`tools-file-ops/scripts/constants.py:40`). |
| `work/metrics-dispatch-boundaries-{phase}.toon` | `manage-metrics.py:2599` `cmd_record_dispatch_boundary` | **3 of 6 phases in practice.** Gated on `PHASE_NAMES`, but only 3 dispatch classes call it; the other 6 are named in `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` (`manage-metrics.py:398`). |

⭐ **VERDICT: the populations differ BY CONSTRUCTION, and no ledger is a subset of another.** The
`execution_log` cannot record phases 1–4 at all; the boundary files cannot record the 6 excluded dispatch
classes; `metrics.toon` holds a per-phase *aggregate* rather than rows, so it cannot express a repeat count.
D1's writer-side derivation is decisive on its own, exactly as the plan predicted it might be. **The plan is
not re-scoped away on this axis** — D3/D4/D5/D6 stand unchanged.

### Repeated-step counts — structurally confirmed, arithmetically unverifiable here

`cmd_record_step` appends one row per invocation (`manage-execution-manifest.py:2659`);
`cmd_record_dispatch_boundary` appends one row per dispatch termination (`manage-metrics.py:2692`). The two
call sites are **independent** — no shared transaction, no shared key, and the boundary row carries **no
`step_id` at all** (its schema is `rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,+4}`,
`manage-metrics.py:2711`). A step re-dispatched without a matching `record-step`, or recorded without a
boundary row, therefore lands in one ledger and not the other **in both directions**. The plan's specific
"twice / three times / four in the union" figures are first-party artifact counts and are **not re-derivable
in this clone**; they are treated as LEADS and are not cited as measured results anywhere in this change.

### ⛔ D1 REFUTES one load-bearing claim, and sharpens another

The plan states the `actual_tokens` sum is *"compared against a **whole-plan** cost prediction, and fed into a
recalibration loop"*, latent only because *"on the observed run the prediction was absent"*. Re-derivation
finds something different, and materially so:

1. **`status.metadata.execution_profile_cost_preview` has NO PRODUCER anywhere in the tree.** The only
   in-tree references are the reader (`check-routing-decisions.py:572`), its own docstring, and a test that
   seeds the key by hand (`test_plan_retrospective_manifest.py:1012`). `phase-1-init/SKILL.md` Step 8d
   resolves the per-posture preview, **shows** `cost_sum_tokens` to the operator in the `AskUserQuestion`
   options, and persists **only** `execution_profile` (`phase-1-init/SKILL.md:922-925`). So `predicted_tokens`
   is `None` on **every** run, and `delta_tokens` / `delta_pct` are **never** emitted. The defect is latent
   **by construction**, not by accident of one run — a stronger statement than the plan's.
2. **The only candidate producer would supply a phase-6-only prediction, not a whole-plan one.**
   `cmd_preview_lanes` (`manage-execution-manifest.py:1786`) computes `cost_sum_tokens` as
   `Σ(resolved element cost_size → cost_size_token_table)` over `phase_6_steps` **alone**. Wired up, the
   prediction would cover **1 of 6 phases** while the "actual" covers **2 of 6** — a mismatch in the
   **opposite direction** from the plan's hypothesis (the actual would exceed the prediction's population,
   not halve it).

⇒ **D2 keeps its deliverable and loses its rationale.** The defect is not "a partial actual versus a
whole-plan prediction". It is that a **2-of-6-phase sum is named `actual_tokens`** and is wired into a
comparison whose comparand has no producer — so the mismatch would be introduced, silently and plausibly, the
moment anyone connects one. The fix D2 asks for (name the population; refuse or annotate a
population-mismatched comparison) is unchanged and becomes *more* valuable, because it makes the wiring safe
in advance rather than after a corrupted recalibration.

### Blast-radius arm (claim-label row 3)

The plan flags: *"if a prior run DID carry a prediction, the recalibration table may already be corrupted."*
**Closed: it cannot have.** With no producer for the key, no run has ever carried a prediction, so
`delta_tokens` / `delta_pct` have never been emitted and `cost_size_token_table` has never been recalibrated
from this path. No blast-radius arm is opened.

### Other claim labels re-derived at the gate

| Claim | Verdict | Artifact |
|---|---|---|
| The cost-preview evaluation sums one ledger and emits it as the actual | **CONFIRMED** | `check-routing-decisions.py:571,578` — `sum_execution_log_tokens(manifest)` → `'actual_tokens'` |
| The aggregate and its qualifier are render-time only | **CONFIRMED** | `manage-metrics.py:1384` `write_metrics` runs **before** the Total row is built at `1610-1629`; the store's header carries no aggregate |
| The disambiguating caveats are render-only | **CONFIRMED** | every annotation is a bare `lines.append(...)` after the store write — `manage-metrics.py:1653-1724` |
| An inline-cost field is sparsely persisted | **CONFIRMED** | `cmd_enrich` writes `inline_main_context_tokens` only on a truthy inline sum (`manage-metrics.py:3082-3093`) |
| A population marker already exists in one rendered report | **CONFIRMED in-tree** | `_TOKENS_COLUMN_HEADER = 'Tokens (dispatched unless marked)'` (`manage-metrics.py:235`) + `_POPULATION_CELL_SUFFIX` |
| A completeness verdict keys a phase's recorded status solely off its end timestamp | **CONFIRMED** | `phases_missing_end_time` predicate, `manage-metrics.py:1363-1365` |
| A per-task duration is wall-clock derived | **CONFIRMED** | `plan-efficiency.md:104` — `seconds_per_task = totals.duration_seconds / max(tasks_completed, 1)`; `duration_seconds` is the accumulated **wall** span (`_accumulate_duration_seconds`, `manage-metrics.py:892`), while the worked figure `agent_duration_seconds` is recorded separately |
| The persistence loop hardcodes its field list | **CONFIRMED** | `cmd_enrich`'s inline literal tuple at `manage-metrics.py:3000-3005`, against the canonical `_FOUR_FIELD_USAGE_LABELS` (`manage-metrics.py:259`) the **render** loop walks |
| The population vocabulary is supplied by another epic and lands first | **SATISFIED** | `TOKEN_POPULATIONS` is already in-tree (`manage-metrics.py:226`); this plan consumes it and defines no new member |
| The partiality keys were renamed with no dual-key shim | **CONFIRMED, and deliberate** | `manage-metrics.py:1376-1377` pops `partial` / `unrecorded_phases` as a write-side refusal |

## Split-guard verdict (recorded per the plan's instruction)

**Verdict: DO NOT SPLIT — executed as one unit.** The natural cut the plan names (D1+D2+D4 reconciliation /
D3+D5+D6 persistence) was evaluated and rejected on three grounds recorded here:

1. **D4 consumes what D3 persists.** The reconciliation's declared-exclusion output is derived from the same
   population constants D3 persists; split across two PRs, the second would restate the first's vocabulary.
2. **The plan's own Notes forbid concurrency** — *"Several sibling plans edit the same bundle — sequence,
   never run concurrently."* Two PRs over `manage-metrics` would have to be serialised anyway, buying nothing
   and doubling the merge-queue passes.
3. **The lane is one plan → one PR.** Splitting would require authoring a second plan file, which is an
   orchestrator act outside this run's remit.

## Deliverables

_Filled in as each lands._

## Build gate

_Pending._

## Findings

_Pending._

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
