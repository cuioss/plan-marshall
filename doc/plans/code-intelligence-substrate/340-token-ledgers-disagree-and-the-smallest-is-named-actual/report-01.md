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

⚠ **Every line number in this section is an `origin/main` line number** — the state the gate was run against.
This plan's own changes move several of them; cite the symbol, not the line, when reading against the merged
tree.

### The three ledgers, and their populations by construction

| Ledger | Writer | Population it can hold |
|---|---|---|
| `execution.toon` → `execution_log[]` | `manage-execution-manifest/scripts/manage-execution-manifest.py:2600` `cmd_record_step` | **2 of 6 phases.** `VALID_RECORD_PHASES = ('5-execute', '6-finalize')` (`_manifest_core.py:247`), enforced by a hard `invalid_phase` refusal at `manage-execution-manifest.py:2618`. |
| `work/metrics.toon` phase rows | `manage-metrics/scripts/manage-metrics.py:975` `_close_phase_accumulating` (via `end-phase` / `phase-boundary`) | **6 of 6 phases.** Gated on `PHASE_NAMES = list(PHASES)`, i.e. `1-init … 6-finalize` (`tools-file-ops/scripts/constants.py:40`). |
| `work/metrics-dispatch-boundaries-{phase}.toon` | `manage-metrics.py:2599` `cmd_record_dispatch_boundary` | **3 of 6 phases in practice.** Gated on `PHASE_NAMES`, but only 3 dispatch classes call it; the other 6 are named in `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` (`manage-metrics.py:398`). |

⭐ **VERDICT: the populations differ BY CONSTRUCTION, and no ledger is a subset of another.** The
`execution_log` cannot record phases 1–4 at all; the boundary files cannot record the 6 excluded dispatch
classes; `metrics.toon` holds a per-phase *aggregate* rather than rows, so it cannot say WHICH dispatches
it summed — only how many times the phase closed (`close_count`).
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

| # | What was done | Commit | Verification state |
|---|---|---|---|
| **D1** | Hard gate. Re-derived the three ledgers' populations from their **writers** (the artifacts are git-ignored and absent from this clone, which is the plan's stated fallback). Mutates nothing. Findings above. | `c39363a`, `0485ef3` | Every code citation re-checked against `origin/main` by the round-1 verifier; all land on the symbol claimed |
| **D2** | `actual_tokens` → `execution_log_tokens`, published beside `execution_log_population`. The comparison is gated on population equality: `delta_tokens` / `delta_pct` only when `comparison: computed`; a mismatch (including an `unstated` prediction population) is `refused` with a reason. | `7b303a0` | 5 behavioural tests + 2 contract-drift tests; refusal gate and mirrored phase set both mutation-tested |
| **D3** | Each Total column persists a triple (value, `_population_count`, shared denominator), plus `totals_tokens_spans_populations`, `totals_sampled_at` and `dispatch_boundary_excluded_classes`. The render reads the store back rather than holding a second copy. `inline_main_context_tokens` is completed on every row — a measured `0` where `enrich` stamped it, `unmeasured` where it never visited. The aggregate is invalidated by any non-`generate` write. | `d52dea8`, round-1 fixes | Round-trip test over every column; population-count guard mutation-tested against the pre-fix state; invalidation guard mutation-tested |
| **D4** | Read-only `reconcile-ledgers` verb + `_ledger_reconciliation.py`. Joins `execution_log[]` against each phase's boundary file on phase + timestamp window, one finding per unpaired row in each direction. `boundary_never_closed` and `phase_re_entered` are separate shapes from `row_absent_from_*`. Structural exclusions declared, unreadable manifest → `not_evaluated`. Publishes `union_rows`. | `f97455d` | 15 tests, each shape with a negative control; three guards mutation-tested |
| **D5** | An unclosed phase's boundary sum is folded into its Tokens cell and marked `(boundary floor)`, with `tokens_cell_source: unclosed_boundary_floor` persisted. Fires both where the sum was refused as partial/over and where it silently won the maximum unlabelled. Duration partiality untouched. | `d52dea8`, round-1 fixes | 7 tests; the `end_time` guard and the cell marker both mutation-tested |
| **D6** | Arm 1: `seconds_per_task` → `worked_seconds_per_task`, reading the recorded worked figure rather than wall clock; no clamping, no gap heuristics. Arm 2: the `enrich` persistence loop derives its field list from `_FOUR_FIELD_USAGE_LABELS`. | `d52dea8`, round-1 fixes | Arm 1: 3 tests over a real 8-hour idle gap, including a positive control that drives a worked-exceeds-wall row through `end-phase` and observes it clamped — so the untouched value on the idle-gap row is a property of that row, not of a clamp that never runs. Arm 2: source-level guard that the retired literal loop has not returned |
| **D7** | (a) divergent rows → per-row findings; (b) population-mismatched comparison refused; (c) a Total rendered without a persisted population marker fails. | across the above | (a) and (b) fail against their named defect; (c) fails against a faithful pre-fix mutant (render the qualifier, persist nothing) |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` names **9 Python files**, so the gate applies.

`./pw verify` → **`=== verify: SUCCESS ===`**, `20831 passed, 14 skipped` (403 s). Per-commit `./pw quality-gate` before every commit touching `*.py`: `ruff … All checks passed!`, `mypy … Success: no issues found`, `SPDX-header check passed`, plugin-doctor `issues[0]`. No `uv.lock` churn at any commit (`git status` checked before each).

⚠ **`test-compile` earned its place.** The first `./pw verify` failed with two `no-any-return` errors in the new metrics test module — a sub-step neither `quality-gate` nor `module-tests` performs, both of which were green on that same file. Fixed in `e978619`.

## Findings

One row per instance. Round-1 findings come from the independent verification sub-agent.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | round 1 | `plan-efficiency.md` fragment template read `totals_worked_ms` / `totals_wall_ms` into fields named `_seconds` with no conversion — a 1000× error that would trip the threshold on essentially every plan | **fixed** — explicit `/ 1000` in the template and a ⛔ note on the Inputs bullet |
| F2 | round 1 | The `(boundary floor)` annotation, `_unclosed_boundary_floor.__doc__` and `data-format.md` all claimed an unclosed phase "has no recorded total" and that "its duration stays absent". Both false when the accumulator backfill supplies them | **fixed** at all three sites; the claim now scopes to *the fold*, and names the accumulator as the other route |
| F3 | round 1 | `test_the_duration_partiality_verdict_survives_the_fold` reached its asserted state by a different route than it named — its boundary-only fixture rendered `-` because nothing was recorded, not because the fold withheld it. Could not fail against the defect it names | **fixed** — fixture now gives the phase an accumulator, so Worked *is* populated and the wall cell's `-` is attributable to the fold |
| F4 | round 1 | "`metrics.toon` … cannot express a repeat count at all" — contradicted by the same module reading `close_count` from it | **fixed** in both `_ledger_reconciliation.py` and `SKILL.md` |
| F5 | round 1 | `execution_rows_for_phase.__doc__` named `timestamp` where the code sets `parsed_timestamp` | **fixed** |
| F6 | round 1 | "the returned second-scale value and the persisted millisecond value are the same measurement" — false, the `_seconds` keys round to one decimal | **fixed**; the comment now states the rounding and points readers at `totals_*_ms` for the exact figure |
| F7 | round 1 | The `end_time`-presence annotation said unclosed rows' "totals are absent", which the same report now contradicts by rendering a boundary floor for one | **fixed** — reworded to distinguish "no close recorded them" from "no figure is shown" |
| F8 | round 1 | `data-format.md`'s three-signature table still said `inline_main_context_tokens` is "not written" on a dispatched row | **fixed** |
| F9 | round 1 | `SKILL.md`'s `generate` **Output** example and its prose enumeration omitted every new return field | **fixed** — example and prose both extended |
| F10 | round 1 | `worked_seconds` labelled "the ratio denominator"; it is the numerator | **fixed** |
| F11 | round 1 | `comparison_reason` documented as unconditional; it is absent on `computed` | **fixed** in the fragment shape and the fact table |
| F12 | round 1 | `§4.6a` resolves nowhere in the tree; this change propagated the dangling reference into two new production docstrings | **fixed** at all four sites — replaced with a resolvable pointer to `cost-sizing.md` |
| F13 | round 1 | The run report was unfinished — `_Pending._` in every section after D1 | **fixed** — this table and the sections around it |
| F14 | round 1 | `fixtures/archived-plan/work/fragment-plan-efficiency.toon` still carried `seconds_per_task`, passing silently because nothing asserts the key name | **fixed** — fixture carries `worked_seconds` and `worked_seconds_per_task` |
| F15 | round 1 | **Invented rationale, refuted by execution.** I wrote that worked time is bounded above by the wall span, so the threshold "fires strictly less often … introduces no false warnings". `subagent_duration_ms` is written by `enrich` with no clamp and `_worked_ms` takes the max, so Worked can and does exceed Reported (wall) | **fixed** — the claim is withdrawn and replaced with what is verifiable: the threshold is *unanchored* for the new numerator, and may fire more often as well as less |
| F16 | round 1 | D6 arm 1 had no verification of any kind, though the plan named one ("verified against a case containing a long idle gap … must not be achieved by clamping") | **fixed** — `TestWorkedTimeExcludesTheIdleGap`: three tests over an 8-hour gap with a 10-minute worked span, including a positive control that drives a worked-exceeds-wall row through the same `end-phase` path and observes it clamped |
| — | round 2 | Commit `82ee8ad`'s message says "Seventeen findings"; that commit closes **18** (F1–F17 and F20). Git history is immutable once pushed, so the count is corrected here rather than by rewriting a pushed commit | **corrected in the record** |
| F17 | round 1 | The persisted aggregate went stale on any non-`generate` write, with nothing marking it stale — while the new contract tells consumers to *read* it | **fixed, and by a stronger mechanism than proposed.** A timestamp comparison cannot work here (both stamps are second-granularity, so a same-second write is invisible — demonstrated by the test that first exposed it). `write_metrics` now **drops** every aggregate key for any writer that did not just compute it, making the aggregate present-iff-fresh |
| F20 | round 1 | `generate` became all-or-nothing when the store write moved past the render; a semantics change nothing named | **fixed** — the bound is now recorded at the site: every read between the two points goes through `_coerce_numeric` / `_numeric`, which return `None` rather than raising |
| — | self (round 1 fixes) | My own writer list — "`end-phase` / `phase-boundary` / `enrich` / `accumulate-agent-usage`" — was wrong in three places: `start-phase` writes the store and `accumulate-agent-usage` does not | **fixed** at all three sites after re-deriving the call sites from source |
| — | self (during implementation) | `test_a_closed_phase_takes_no_floor_marker` passed for the wrong reason: its recorded total exceeded the boundary sum, so the cell could never be marked a floor whether or not the `end_time` guard existed | **fixed** before commit — the control now closes with a total *below* the boundary sum, so the guard is the only thing withholding the marker (verified by mutation) |
| — | self (during implementation) | The window test paired at gap zero, asserting nothing about the window | **fixed** before commit — a real 10-minute offset with an in-test positive control at a wider window |
| — | round 1 | `POPULATION_UNSTATED = 'unstated'` is a coined value in a `*_population` field, beside a comment insisting the script authors no vocabulary | **rejected, with reason.** It names the *absence* of a population claim, not a population; the plan's ⛔ scopes to `TOKEN_POPULATIONS`, which is untouched. Renaming it to a phase-set-shaped value would assert a population the record does not carry |
| F18 | round 1 | `reconcile-ledgers` has no caller; nothing invokes it in any workflow | **survivor** — see the stop record |
| F19 | round 1 | The D3/D5 guards' pre-fix failure is a module-level collection error, not a per-assertion demonstration | **survivor** — see the stop record |
| R2-F1 | round 2 | F7's fix reached 1 of 2 sites: `data-format.md`'s rendered example still quoted the refuted "their totals are absent" verbatim | **fixed** — the example is now synced to the renderer's actual string |
| R2-F2 | round 2 | `SKILL.md`'s `generate` **Output** example was unproducible: it showed `phases_missing_end_time: 6-finalize` alongside wall/idle population counts of 6, which an unclosed phase makes unreachable | **fixed** — counts corrected to 5 with the derived seconds/formatted figures re-derived through `format_duration` |
| R2-F3 | round 2 | "the phase's aggregate is what is missing" survived at three untouched sites — including the `detail` string this change **emits into the verb's output** | **fixed** at all three; the claim now says what no *close* recorded |
| R2-F4 | round 2 | `TOKENS_SOURCE_UNCLOSED_BOUNDARY`'s comment claimed the boundary file is "the **only** durable record" and that dropping it renders the phase `-`; both false when the accumulator backfills | **fixed** — names both close-independent records and states the fold takes the larger |
| R2-F5 | round 2 | "drops **every** aggregate key" overstated at three sites: `dispatch_boundary_excluded_classes` is in the aggregate's field table and is deliberately *not* dropped | **fixed** — scoped to the row-derived `totals_*` family, with the exception and its reason recorded |
| R2-F6 | round 2 | `SKILL.md` named `phase-boundary` among the verbs that leave the aggregate absent; it regenerates unconditionally as its own last step | **fixed** — the invalidation is now stated as a property of the *write*, with the verb's self-healing named |
| R2-F7 | round 2 | F20's own new comment said `_coerce_numeric` returns `None`; it returns the original value | **fixed** — the two functions are now described separately, and the load-bearing half ("neither raises") is kept |
| R2-F8 | round 2 | F4's sweep counted 2 sites where the claim spans 3 — the third being this report's own D1 verdict | **fixed** |
| R2-F9 | round 2 | Report figure wrong: D5 stated 8 tests; `TestUnclosedBoundaryFold` has 7 | **fixed** — every test count in this report re-derived by collection at the moment of the claim |
| R2-F10 | round 2 | Commit `82ee8ad`'s message says "Seventeen findings"; it closes 18 | **corrected in the record** (row above) — pushed history is not rewritten |
| R2-F11 | round 2 | `test_the_idle_residual_is_the_gap` asserted `idle == wall - worked`, which is how the value is computed — it pinned neither operand and stayed green under the mutant that failed its sibling | **fixed** — asserts against the fixture's own constants; re-run under that same mutant, it now fails |
| R2-F12 | round 2 | The clamp positive control called the helper directly, proving the function rather than the wiring — and the report overstated it as "proving the clamp is live" | **fixed** — the control now drives a worked-exceeds-wall row through `end-phase` and observes it clamped; both report phrasings corrected |

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
