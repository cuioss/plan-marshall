# Run report — 340-token-ledgers-disagree-and-the-smallest-is-named-actual (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/token-ledgers-disagree-q3t771` (harness-assigned)
**PR:** [#1293](https://github.com/cuioss/plan-marshall/pull/1293)    **Outcome:** completed — deliverables complete, required checks green, auto-merge armed on the operator's instruction (landing delegated to the merge queue)

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
| **D2** | `actual_tokens` → `execution_log_tokens`, published beside `execution_log_population`. The comparison is gated on population equality: `delta_tokens` / `delta_pct` only when `comparison: computed`; a mismatch (including an `unstated` prediction population) is `refused` with a reason. | `7b303a0` | 11 behavioural tests + 2 contract-drift tests + 2 population-filter tests; refusal gate and mirrored phase set both mutation-tested |
| **D3** | Each Total column persists a triple (value, `_population_count`, shared denominator), plus `totals_tokens_spans_populations`, `totals_sampled_at` and `dispatch_boundary_excluded_classes`. The render reads the store back rather than holding a second copy. `inline_main_context_tokens` is completed on every row — a measured `0` where `enrich` stamped it, `unmeasured` where it never visited. The aggregate is invalidated by any non-`generate` write. | `d52dea8`, round-1 fixes | Round-trip test over every column; population-count guard mutation-tested against the pre-fix state; invalidation guard mutation-tested |
| **D4** | Read-only `reconcile-ledgers` verb + `_ledger_reconciliation.py`. Joins `execution_log[]` against each phase's boundary file on phase + timestamp window, one finding per unpaired row in each direction. `boundary_never_closed` and `phase_re_entered` are separate shapes from `row_absent_from_*`. Structural exclusions declared, unreadable manifest → `not_evaluated`. Publishes `union_rows`. | `f97455d` | 19 tests, each shape with a negative control; three guards mutation-tested, and the matching brute-forced against exhaustive enumeration over 3 000 random corpora (0 non-maximal, 0 order-dependent reports) |
| **D5** | An unclosed phase's boundary sum is folded into its Tokens cell under a marker naming how far it can be trusted — `(boundary floor)` where coverage is partial or undecidable, `(boundary sum, over-covering)` where the file holds more rows than sampled dispatches — with the matching `tokens_cell_source` persisted. Fires both where the sum was refused by the eligibility rules and where it silently won the maximum unlabelled. Duration partiality untouched. | `d52dea8`, round-1 fixes | 12 tests (7 fold + 5 over-covering, the latter with a `partial`-coverage negative control); the `end_time` guard and the cell marker both mutation-tested |
| **D6** | Arm 1: `seconds_per_task` → `worked_seconds_per_task`, reading the recorded worked figure rather than wall clock; no clamping, no gap heuristics. Arm 2: the `enrich` persistence loop derives its field list from `_FOUR_FIELD_USAGE_LABELS`. | `d52dea8`, round-1 fixes | Arm 1: 3 tests over a real 8-hour idle gap, including a positive control that drives a worked-exceeds-wall row through `end-phase` and observes it clamped — so the untouched value on the idle-gap row is a property of that row, not of a clamp that never runs. Arm 2: source-level guard that the retired literal loop has not returned |
| **D7** | (a) divergent rows → per-row findings; (b) population-mismatched comparison refused; (c) a Total rendered without a persisted population marker fails. | across the above | (a) and (b) fail against their named defect; (c) fails against a faithful pre-fix mutant (render the qualifier, persist nothing) |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` names **9 Python files**, so the gate applies.

`./pw verify` locally at each gate point → **`=== verify: SUCCESS ===`**, most recently `20852 passed, 14 skipped` (375.9 s). Re-run after every round; that figure is the last local one, not an earlier round's. **CI is the authority on the head**: `verify / conclusion` → `success` on `f1b9eb9`. Per-commit `./pw quality-gate` before every commit touching `*.py`: `ruff … All checks passed!`, `mypy … Success: no issues found`, `SPDX-header check passed`, plugin-doctor `issues[0]`. No `uv.lock` churn at any commit (`git status` checked before each).

⚠ **`test-compile` earned its place.** The first `./pw verify` failed with two `no-any-return` errors in the new metrics test module — a sub-step neither `quality-gate` nor `module-tests` performs, both of which were green on that same file. Fixed in `e978619`.

## Findings

One row per instance — **58 rows**: 55 from the four verification rounds (21 / 13 / 7 / 14 by round) plus 3 caught by this run itself during implementation. Counted from this table at the moment of writing, not carried forward.

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
| F17 | round 1 | The persisted aggregate went stale on any non-`generate` write, with nothing marking it stale — while the new contract tells consumers to *read* it | **fixed, and by a stronger mechanism than proposed.** A timestamp comparison cannot work here (both stamps are second-granularity, so a same-second write is invisible — demonstrated by the test that first exposed it). `write_metrics` now **drops the row-derived `totals_*` family** for any writer that did not just compute it, making the aggregate present-iff-fresh. `dispatch_boundary_excluded_classes` is deliberately kept — it derives from a module constant, not from the rows |
| F20 | round 1 | `generate` became all-or-nothing when the store write moved past the render; a semantics change nothing named | **fixed** — the bound is now recorded at the site: every read between the two points goes through `_coerce_numeric` (which falls back to the original value) or `_numeric` (which returns `None`), neither of which raises |
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
| R3-F1 | round 3 | The "drops **every** aggregate key" overclaim survived at a 4th site — the report row that declares it fixed | **fixed** |
| R3-F2 | round 3 | Same family, 5th site: a test comment and docstring stating the rule unqualified, with no assertion covering the kept key | **fixed** — and the test now *asserts* `dispatch_boundary_excluded_classes` survives, so the scope is pinned rather than described |
| R3-F3 | round 3 | The `_coerce_numeric`-returns-`None` falsity survived in the report row that declares it fixed | **fixed** |
| R3-F4 | round 3 | "the aggregate is what is missing" survived at a 4th site — the test docstring pinning that very finding shape | **fixed** |
| R3-F5 | round 3 | `plan-efficiency.md` was the one site of the freshness rule left unscoped ("every other writer drops it"), which `phase-boundary` contradicts at the verb level | **fixed** |
| R3-F6 | round 3 | `pair_rows` was nearest-first greedy, so a row could take a partner another row needed — stranding both and emitting **two spurious findings** where a perfect pairing exists. A false signal about the ledgers, manufactured by the verb built to surface them | **fixed** — replaced with maximum bipartite matching (Kuhn's), so the unpaired sets are minimal by construction. Regression test uses the exact scenario, with a negative control proving genuine absences are still reported and an order-independence test. The row sort key also moved from the raw timestamp string to the parsed datetime |
| R3-F7 | round 3 | An `over`-coverage boundary sum — which the module itself calls impossible for one population and potentially double-counted — was folded and labelled `(boundary floor)`, asserting a lower bound that classification denies. A false label on a **rendered cell** | **fixed** — `over` coverage now renders `(boundary sum, over-covering)` with `tokens_cell_source: unclosed_boundary_over_covering` and its own annotation. The fold is kept (rendering nothing for a phase that demonstrably spent something is worse); only the claim changes. 5 tests including a `partial`-coverage negative control |

| R4-F1 | round 4 | `pair_rows`' docstring claimed order-independence; the sort was stable but not total, so two same-timestamp rows kept the manifest's order and the same data written differently named a different dispatch. Demonstrated end-to-end through `cmd_reconcile_ledgers` | **fixed** — `_row_sort_key` is now total over the row's own values, and `pair_rows` sorts internally rather than trusting callers (my first fix sorted only in the readers, and the new test caught that) |
| R4-F2 | round 4 | "only the unpaired sets are reported" read as containment while naming the thing that varies: 23% of corpora admit maximum matchings with **different** unpaired sets, and those rows become findings carrying a `step_id` | **fixed** — the docstring now states the limit outright: a finding identifies *a* row that could not be paired, never *the* divergent dispatch, and the per-phase counts are the exact figures. Recorded as a residue below, not papered over |
| R4-F3 | round 4 | The order-independence test used a corpus admitting a perfect matching, so `unpaired == []` under every ordering — vacuous with respect to its own name. A mutant reversing visit order left all tests green | **fixed** — rebuilt on a tied corpus where a row IS left over, with the precondition asserted; a sibling test pins the sort key directly |
| R4-F6 | round 4 | The `end_time`-presence annotation and the over-covering annotation **co-render on every affected report** and contradicted each other: one said every recovered figure is a floor, the other that this one is not | **fixed** in the renderer and its `data-format.md` mirror |
| R4-F7 | round 4 | The over-covering annotation asserted an "upper-bounded estimate", which the declared exclusions deny (6 of 9 dispatch classes register no boundary), and drew double-counting from a mechanism that does not entail it | **fixed** — the figure is now stated as bounded in **neither** direction, with both reasons named |
| R4-F8 | round 4 | `_unclosed_boundary_floor.__doc__` still described the fold as producing a labelled floor, now false for the `over` half the same function feeds | **fixed**, along with a mis-attributed phrase in the neighbouring constant |
| R4-F9 | round 4 | The report's D5 row described the behaviour R3-F7 removed — stating the pre-fix behaviour and its fix simultaneously | **fixed** |
| R4-F10 | round 4 | D4's test count stale (15 → 19), despite R2-F9's remediation being "re-derive every count at the moment of the claim" | **fixed** — every count in this report re-derived by collection at the final commit |
| R4-F11 | round 4 | The build-gate figure recorded a superseded tree (20 831), and nothing said the gate had been re-run after the last two commits | **fixed** — re-run at the final commit and re-stated |
| R4-F12 | round 4 | `evaluate_cost_preview` reported `'no cost preview recorded'` for a value that **is** recorded but unparseable (`'12.5'`, `'abc'`, `'-100'`), and silently discarded a padded `'  42  '` while stripping the population field beside it | **fixed** — present-but-unreadable is now its own reason naming the value; the numeric read is stripped like its neighbour. 4 parametrised cases + a padded case + a negative control keeping absence and unreadability distinct |
| R4-F13 | round 4 | `sum_execution_log_tokens` summed every row regardless of phase while publishing a two-phase population label — the label a promise about another process, not a property of the sum | **fixed** (survivor closed rather than carried) — the sum is filtered to `EXECUTION_LOG_PHASES`. This is the plan's own keeper rule applied to its own deliverable |
| R4-F14 | round 4 | The R3-F6 row claimed a sort-key change with nothing pinning it; a mutation reverting it left the suite green | **fixed** — `test_the_sort_key_is_total_over_the_rows_own_values` pins it directly |
| R4-F4 | round 4 | `_augment` recurses ~0.75·N per phase; `RecursionError` at N≈999 dense, exiting as a traceback rather than a TOON error | **survivor** — see the stop record |
| R4-F5 | round 4, **re-found by `cuioss-review-bot` on the PR** | A zone-naive timestamp would raise `TypeError` in the sort and in `pair_rows` rather than degrading | **fixed** (survivor closed on the reviewer's finding) — `_parse_iso` now reads a bare stamp as UTC, which is what both writers emit explicitly. I had carried this with a bound ("unreachable from the current writers"); the reviewer's remedy is two lines and removes the survivor entirely, which is better than defending the bound. 3 tests, all mutation-verified against the reported `TypeError` |

## Stop record

**Which exit ended the loop: the ROUND BUDGET, not a verifier's "nothing remains".**

The budget was **4 rounds, declared before the first dispatch** — in the turn that launched round 1, not at the
moment of wanting to stop. Round 4 exhausted it. Round 4's own answer to the stop question was **"yes, findings
remain that A or B forbids leaving open"**, and it stated plainly that a fifth round would find more.

Per the lane contract's budget-exit terms, **everything condition A forbids was fixed regardless of the budget**
— all 10 A-violating round-4 findings, plus R4-F3 (which B's own carve-out denies a bound, since it changes a
test's meaning) and R4-F13 (a survivor closed because its fix was three lines and is the plan's own thesis).
Nothing false ships because the rounds ran out.

**Evidence stronger than a read.** Round 4's verdict rests on exhaustive enumeration (4 000 corpora, every
matching enumerated, maximality confirmed 4 000/4 000), a 6-mutant campaign in which **two mutants survived** —
and those two survivors are exactly R4-F14 and R4-F3, neither reachable by reading — differential execution
through the real verbs, tripwire instrumentation of the `_EPOCH` sentinel, and recursion-depth profiling with
binary search for the fault threshold. After the fixes I re-ran the brute-force myself over 3 000 fresh corpora:
**0 non-maximal, 0 order-dependent reports**.

**Were the late rounds' findings narrower? Partly — and the split is the honest answer.** The *prose* findings
did narrow to the run's own record: by round 4, the surviving instances of both corrected claim families were in
the report rows that declare them fixed and in test docstrings, the production sites having been genuinely
corrected. But round 3 was the first round to sweep the **code**, and rounds 3–4 found four shipped-behaviour
defects there — a greedy pairing manufacturing spurious findings, a false `floor` label on a rendered cell, an
emitted reason stating an absence the record contradicts, and a sum whose published population was an assertion
rather than a filter. Those are not narrower; they are new territory that the prose-focused rounds never reached.
The finding counts per round were **21, 13, 7, 14** — not a converging sequence.

### Survivors — each characterised, and each re-put to the verifier in the stopping round

| Survivor | Class | Bound |
|---|---|---|
| **F18** — `reconcile-ledgers` has no caller | B(a) | Re-checked in round 4: 26 references, all definition / registration / SKILL.md / tests / report; **zero workflow call sites**. It cannot change what any run does today, because no run invokes it. D4's stated "Done when" is met — the verb exists, is documented and is tested. Closing it means wiring a call site into a phase workflow, which is a scoping decision this plan did not make. |
| **F19** — the D3/D5 guards' pre-fix failure is a module-level collection error | B(a) | The test module binds production constants at import, so a pre-fix revert cannot collect. Bound, and **strengthened** across rounds: rounds 2–4 individually mutation-tested those guards (each failed against the defect it names), which is stronger evidence than a collection error would have been. Closing it means restructuring the module to defer constant binding — no behavioural gain. |
| **R2-F10** — a pushed commit message states 17 findings where it closes 18 | B(b) | Bound: pushed git history is immutable without a force-push, which the lane's durability discipline forbids for a cosmetic correction. Reach: one commit-message line. The correction is recorded in this table. |
| **R4-F4** — `_augment` recursion cliff at N≈999 rows per phase | B(b) | Bound: needs ~1 000+ rows on **both** sides of a single phase; measured thresholds are N≈999 dense and N≈1 329 at 120 s spacing (a 44-hour phase). Contained by F18 — only a manual invocation reaches it at all. Promise: it stays outside any plan whose phase records under ~1 000 dispatches, which is every plan the corpus has produced. Closing it means an iterative rewrite of `_augment`. |
| **R4-F2 residue** — which unpaired row a finding names | B(b) | Not a defect to fix: inherent to reporting unpaired rows under any maximum matching. Bound: the per-phase **counts** are exact and order-independent (verified over 3 000 corpora); only a row's *identity* is settled by the traversal where several rows were equally pairable. Now stated in the docstring as a limit of the verb. |

### What residue to assume remains

⛔ **Do not read this as a converged loop.** The defect class never changed across four rounds: *a claim written
beside the code it describes, true for the case in front of the author and false for the neighbouring case,
corrected at n−1 of n sites.* Round 4 found six more instances, **two of them manufactured by round 3's own
fixes**, and two more at sites round 3's sweep should have reached. Every fix writes new unreviewed prose, so
the rate is self-sustaining rather than decaying.

Concretely, a reader should assume:

- **More instances of the same claim families exist**, most likely in this report's own dispositions — the
  densest residue site across rounds 2, 3 and 4. Treat every "fixed at all N sites" row as a claim needing the
  same verification as the code.
- **At least one further test in the new modules probably asserts a property it cannot fail on.** That family
  already has five instances (F3, R2-F11, R4-F3, and two caught during implementation), and only the rounds that
  *executed* mutations found them — reading a test's name and believing it is exactly how they survive.
- **Any figure not re-derived at the moment of writing is stale.** Two were, in a report that had already
  adopted re-derivation as its rule.

## Reviewer participation

Population **derived from configuration** — the `author_login` of each registry doc under
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/` (`pr-agent.md`, `coderabbit.md`,
`sourcery.md`). Not transcribed from memory. All three comment surfaces were read
(`get_comments`, `get_reviews`, `get_review_comments`); each verdict comes from the stored bodies, never
from a check state.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | **`reviewed`** | — | Posted a *PR Reviewer Guide* naming one focus area: `_parse_iso` parsing a zone-less stamp naive, so mixing awareness raises `TypeError` in the sort and in `pair_rows`. **Fixed** (see the R4-F5 row) and answered on the thread. Its `review / review` check concluded `success` |
| `coderabbitai` | **`rate-limited`** | **yes** | *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. **Next review available in: 24 minutes.**"* A countdown, not a property of this diff |
| `sourcery-ai` | **`rate-limited`** | **no** | *"your pull request is larger than the review limit of 150000 diff characters"* — a size ceiling. Waiting cannot clear it; the same request never succeeds at this diff size. Its `Sourcery review` check concluded `skipped`, consistent with the refusal |

⚠ **Two reviewers refused at the same moment for opposite reasons**, which is exactly why the `Reopens?`
column exists: `coderabbitai`'s window clears on a clock and was worth re-requesting, `sourcery-ai`'s never
will at this diff size. A table without the column would have rendered them identically.

**Coverage: see the merge-gate disclosure below.** No `silent` verdict arose, so no recovery check was
needed — the one reviewer whose body was absent on the first read had simply not finished (its comment
landed at 10:59:56, after that read), which a second read established rather than a `silent` record.

⛔ **No verdict is `unreadable`.** All three surfaces returned cleanly, and the PR payload's own
`comments` count agreed with the bodies read — the positive control against believing an empty result.
Merge-gate condition 2 is therefore genuinely established, not assumed.

## Cost

- **Tokens:** **not available to the agent in this session.** The harness exposes no usage counter to the
  running agent, and no figure is invented here. The four verification sub-agents each reported their own
  usage on return — 279 458 / 278 356 / 214 719 / 225 251 sub-agent tokens, **998 K in total across the
  four** — which is the only measured token figure this run holds. It excludes the main session entirely.
- **Wall-clock:** **3 h 19 min** — first commit `c39363a` at 07:38:45 UTC to final commit `394053d` at
  10:57:53 UTC (source: `git log --date=iso`). Of that, **1 h 45 min** was the four verification agents'
  own reported durations (1 142 s / 2 813 s / 852 s / 1 503 s), i.e. **a little over half the elapsed time
  was spent verifying rather than building.**
- **Population:** these figures count **one Claude Code cloud session's git-observable span, plus four
  dispatched sub-agents' self-reported usage**. ⛔ **NOT comparable to a plan-marshall `metrics.toon`
  total**, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing
  boundary — a boundary this session does not share and cannot reconstruct. The two cannot be reconciled,
  and no attempt is made to present them as though they could be. That is this plan's own subject applied to
  its own cost line.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **done** | Named above; all obtained by bundle path (plugin absent in this session) |
| 2 Branch | **done** | `claude/token-ledgers-disagree-q3t771` — **harness-assigned**, kept as-is per the cloud-session rule. Published to `origin` before the first edit; the plan's `Branch prefix: fix` is superseded by that rule and the divergence is recorded here |
| 3 Plan directory | **done** | `doc/plans/code-intelligence-substrate/340-…/plan.md` exists via `git mv`; the first-instruction block was present and needed no repair |
| 4 Implement | **done** | 12 commits **including this report's own final commit**, each carrying the `Co-Authored-By` trailer and none carrying a "Generated with" footer — both verified by walking `git log origin/main..HEAD`, not asserted |
| 4 Per-commit gate | **done** | Every commit touching `*.py` preceded by `./pw quality-gate` reporting `ruff … All checks passed!`, `mypy … Success: no issues found`, `SPDX-header check passed`, plugin-doctor `issues[0]` |
| 4 Pushed | **done** | Pushed after every commit; no unpushed commit remains |
| 5 Build gate | **done** | 9 `*.py` files in the diff → gate applies. `./pw verify` → `SUCCESS`, 20 852 passed, 14 skipped |
| 6 Verification sub-agent | **done** | 4 rounds; findings and dispositions in the table above; stop record states the **budget exit**, the budget declared before round 1, and each survivor's bound |
| 7 PR cycle | **done** | PR #1293; no `skip-bot-review` (the diff touches `*.py` and `marketplace/bundles/**`, and a skill is code). All three comment surfaces read |
| 8 Merge gate | **conditions 1–3 met; armed on the operator's instruction immediately after this commit** | Verified on the exact head: `verify / conclusion`, `verify / verify`, `verify / gate`, `dependency-review` and `generate-check` all `success`; `mergeable_state: clean`. Every comment handled, this report pushed as the last pre-merge commit, and the 1-of-3 coverage shortfall disclosed to the operator before arming. Landing confirmation is recorded to the operator, not here — the squash SHA does not exist until the queue lands it |
| 8 Bridge | **done** | No status or bookkeeping write outside this plan's own directory; the report carries the PR number and per-deliverable outcome |
| 9 This check | **done** | This table |
| 9 What have we learned | **done** | Below |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this session). **Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a machine-local build step a cloud run neither performs nor records.

**Tree-claim re-check.** The claims in this report about the *filesystem* (as distinct from the diff) were
re-read at the final commit: the `*.py` diff count is 9, the branch is on `origin`, and `git status` is clean.

## What have we learned (Step 9)

**One contract change is proposed, and it is evidence-backed by all four rounds of this run.**

§ Step 6 tells a run to sweep for restatements of a changed claim, and § "Sweep-and-count" tells it to enumerate
every site before fixing any instance. This run followed both and **still leaked the same two claim families in
every single round** — rounds 2, 3 and 4 each found a fix that had landed at n−1 of n sites. The contract's own
diagnosis is correct but its remedy is under-specified in one concrete way: **it never names the run's own
report as a sweep target.** Every round found surviving instances there, including rows that declare a claim
fixed while restating the refuted wording (R2-F8, R3-F1, R3-F3, R4-F9). The report is the one surface a
re-dispatched verifier reads *last* and an author edits *most*.

**Proposed edit** — to § "Sweep-and-count", after "A contract has surfaces, not a site":

> - **The findings table is a surface of every claim it records.** A row saying "fixed at all N sites" restates
>   the claim it fixed, so the row itself becomes an N+1th site. Grep the corrected wording across the report
>   before marking a row fixed, and re-read the row against the artifact rather than against the memory of
>   having fixed it.

⚠ **Not self-approved, and not shipped in this PR.** Per § Step 9 this requires operator approval and, on
approval, its own `chore/` branch touching only the skill — coupling a contract amendment to whether this plan
lands would mean neither gets read properly. **No operator was reachable in this headless run**, so the proposal
is recorded here for the orchestrator's collect step rather than acted on.

## Residue

- **The verification loop stopped on its budget, not on convergence.** See the stop record for what a reader
  should assume still remains, per instance. The short form: more instances of the same claim families are
  likely, most densely in this report; at least one new test probably asserts a property it cannot fail on; and
  any figure not re-derived at the moment of writing is stale.
- **`reconcile-ledgers` has no caller** (F18). The verb is complete, documented and tested, and D4's stated
  "Done when" is met — but until a phase workflow invokes it, the plan's Goal ("a cross-ledger disagreement
  produces a finding instead of a silent choice") is achieved *in principle* rather than on any run. Wiring a
  call site is the natural next plan; it was not in this plan's scope.
- **The `worked_seconds_per_task > 900` threshold is unanchored** for its new numerator. It was calibrated
  against wall clock and is left at its measured value rather than moved by an invented factor; re-deriving it
  needs a corpus of worked-time observations that does not yet exist.
- **Which unpaired row a reconciliation finding names** is settled by the traversal, not by the ledgers, where
  several rows were equally pairable (~23% of small corpora). The per-phase counts are exact; the row identity
  is not. Stated in the verb's own docstring as a limit.
- **One bounded code survivor**: the `_augment` recursion cliff at ~1 000 rows per phase, contained by F18.
  (The zone-naive-timestamp survivor was closed on the PR reviewer's finding rather than carried.)
