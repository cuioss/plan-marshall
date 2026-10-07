# PLAN-CIS-022: Three token ledgers describe one run, disagree row by row, and the smallest is surfaced as `actual_tokens`

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-30 from the inbound cross-epic message `truthful-signals-019`, itself drained from
> `compose-time-subtractions-drop-steps-009` (PLAN-202, PR #1066, merged `d04ac98ed`).

## Objective

One plan run produces three independent token ledgers. No two agree, and **none is a subset of another**.
One of them is summed and emitted under the field name `actual_tokens`, compared against a whole-plan
cost prediction, and fed into a recalibration loop. Make a token figure carry its population, and stop a
partial total from being named "actual".

## Why this is ours

Accepted from `truthful-signals`, who routed it here and invited push-back. We agree with their
reasoning and are **not** returning it: the subject is **measurement of our own runs — how we count** —
which is ours by the standing rule, and there is precedent in the metrics loop-back under-attribution
item (PLAN-10, #1059) routing the same way. Routing goes by subject, not by which theme it echoes.

## The measurement, as reported

| Ledger | Total | Actual population |
|---|---|---|
| `work/metrics.toon` → `metrics.md` | 3,309,881 | phases 2-refine … 5-execute. **1-init and 6-finalize contribute nothing.** |
| `execution.toon` `execution_log[]` | 1,700,331 | 6-finalize dispatched steps only; the four phase-5 `verify:*` rows recorded as `0`. |
| `metrics-dispatch-boundaries-{phase}.toon` | 2,842,524 | 4-plan + 5-execute + 6-finalize dispatch terminations. |

Row-by-row in the 6-finalize window: `execution_log` records **12** non-zero finalize dispatches, the
dispatch-boundary file records **10**, **eight are common**. Two values appear only in the
dispatch-boundary file; four only in `execution_log`.

⭐ **The sharpest consequence:** `pre-submission-self-review` ran **four** times. `execution_log` shows
two. The dispatch-boundary file shows three. **Only the union shows all four — and nothing tells a
reader to take the union.**

## The live defect half

`check-routing-decisions.evaluate_cost_preview` sums `execution_log[].total_tokens`, emits it under the
field name **`actual_tokens`**, compares it against `status.metadata.execution_profile_cost_preview` — a
**whole-plan** prediction — and feeds the signed delta into the §4.6a `cost_size_token_table`
recalibration loop.

⛔ **Latent, not dormant.** On the observed run `predicted_tokens` was `null`, so nothing recalibrated.
**Any run that does carry a preview gets its cost model recalibrated against roughly half its real
spend, under a field name claiming to be the actual.** A partial actual compared against a total
prediction produces *plausible* numbers — which is exactly why it would not look wrong.

## Deliverables

1. **D1 — GATE (mutates nothing): re-derive the three totals and the row-level intersection.** ⛔ **The
   forwarding epic explicitly did NOT verify them** and flagged the numbers as the sender's first-party
   report. The three ledger files are on disk under
   `.plan/local/archived-plans/2026-07-30-compose-time-subtractions-drop-steps/`, so the arithmetic is
   checkable without re-running anything. ⚠ **Re-derive the four-vs-two-vs-three self-review count
   too** — a stated count is a sample, and this epic has shipped that error itself.
2. **D2 — `actual_tokens` stops being a partial.** Either rename it to name its population, or widen the
   sum to the union of the ledgers. ⛔ Whichever is chosen, **the comparison against a whole-plan
   prediction must be population-matched** — an unmatched comparison is the defect, not the field name.
3. **D3 — every token figure carries its population.** ⭐ **The shape already exists in-tree**:
   `metrics.md` prints `(n=4/6)` beside its totals. That partiality marker is precisely what the other
   two ledgers lack, so this is a copy, not a design.
4. **D4 — a deterministic cross-ledger reconciliation** joining the three sources on
   `(phase, step, timestamp window)` and emitting one finding per row present in one ledger and absent
   from another. ⭐ **Pure arithmetic, no judgement — so by the granularity heuristics this is a SCRIPT,
   not a dispatched check.** Build it as one.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A run whose ledgers disagree produces a
   reconciliation finding per divergent row. (b) `evaluate_cost_preview` refuses, or annotates, a
   population-mismatched comparison. (c) A total rendered without a population marker fails the
   assertion.

Five deliverables — under the split guard.

## ⛔ What is NOT ours — do not re-file it

`truthful-signals` is **keeping** their corroborating symptom 1: every per-dispatch context-load column
(`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) reading `0`
on **all 15** rows across three phases — a confident zero where the honest value is *"not captured"*.
It folds onto the `dispatch_boundaries` producerless-row item they already own. ⛔ **Do not scope it
here.**

✅ Their symptom 2 — the retrospective's **Phase Dispatch Boundaries** section reported under
`sections_omitted` (the benign "nothing was lost" bucket) while `analyze-logs` had computed the full
payload — they explicitly did **not** claim, and offered to us. **It is already PLAN-CIS-020's D2.**
⭐ This message therefore **RESOLVES PLAN-CIS-020's mandatory pre-emit cross-epic check**: they own the
zeroed-columns half, we own the render-path half, and the split is now on the record in both ledgers.

## Claim Labels

- **HYPOTHESIS (every figure in the table above)**: the three totals, the 12/10/8 row intersection, and
  the four-vs-two-vs-three self-review count are **the sending plan's first-party report of its own
  artifacts, re-forwarded by a sibling epic that explicitly did not verify them** — confirm/refute by
  reading the three ledger files named in D1 (verify-at-outline). ⛔ **Two hops from the observation and
  zero verifications; treat every number as a lead.**
- **HYPOTHESIS**: `check-routing-decisions.evaluate_cost_preview` sums `execution_log[].total_tokens`
  and emits it as `actual_tokens` — confirm/refute at that symbol (verify-at-outline). **Load-bearing**:
  it is the whole of D2.
- **HYPOTHESIS**: `predicted_tokens` was `null` on the observed run, making the defect latent rather
  than active — confirm/refute at that run's `status.metadata` (verify-at-outline). ⚠ If a prior run
  DID carry a preview, the recalibration table may already be corrupted and D1 grows a blast-radius arm.
- **OBSERVED** (this orchestrator, in-tree): `metrics.md` renders an `(n=4/6)`-style partiality marker,
  so D3's precedent exists. ⚠ Re-confirm the exact form before copying it.
- **Verify-first clause**: ⛔ **D1 is a hard gate — no other deliverable may be scoped until the three
  totals are re-derived.** If the ledgers turn out to agree, or to be subsets after all, D2–D4 change
  shape entirely and this plan is re-scoped rather than continued.

## Expected Surface

- HYPOTHESIS: `plan-retrospective` — `check-routing-decisions`, `evaluate_cost_preview`
  (verify-at-outline)
- HYPOTHESIS: `manage-metrics` — the `work/metrics.toon` writer and the `metrics.md` renderer
  (verify-at-outline)
- HYPOTHESIS: the `execution.toon` / `metrics-dispatch-boundaries-{phase}.toon` writers
  (verify-at-outline; locate via `architecture find` before scoping)
- OBSERVED (read-only fixture corpus):
  `.plan/local/archived-plans/2026-07-30-compose-time-subtractions-drop-steps/`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: ⛔ **PLAN-CIS-013, PLAN-CIS-019, PLAN-CIS-020** — all edit `plan-retrospective`.
  Sequence, never pair.
  ⚠ **PLAN-CIS-014** (`aggregate-cost-invisible-to-per-call-ceiling`) is the closest neighbour: both are
  token-accounting integrity. **They are NOT the same plan** — CIS-014 owns per-call truncation at the
  `platform-runtime` / hook layer, this one owns cross-ledger reconciliation at the metrics layer. ⛔ Do
  not merge them; **do re-check for surface overlap at emit time**, and prefer sequencing them.
- ⚠ **PLAN-CIS-008** consumes token anchors, so its baseline shifts if D2 changes what `actual_tokens`
  means. Prefer landing this first, or record the dependency explicitly when scoping CIS-008.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-022-token-ledgers-disagree-and-the-smallest-is-named-actual.md"
```

## Relation to the epic

⭐ **The keeper rule, and it is the plan's success criterion:** ***a token figure must carry its
population or it must not be named "actual."*** This is the measurement half of the epic's thesis stated
in its most literal form — three ledgers, one run, and the reader is given the smallest without being
told it is partial.

## ⛔⛔ NEW DELIVERABLE — `metrics.md` CARRIES FIGURES THE STORE DOES NOT, so the report is load-bearing rather than presentational (folded 2026-08-03)

**Raised by the operator: *"this form is not accessible for a script for doing math."* Probed
first-party, and the concern is correct in a narrower and sharper way than it looks.**

✅ **The store exists and is good.** `work/metrics.toon` is the machine authority (`parse_toon`),
alongside per-phase `metrics-dispatch-boundaries-{phase}.toon` ledgers and
`metrics-accumulator-{phase}.toon`. It persists `billing_weighted_total`, `dispatch_boundary_total`,
`dispatch_boundary_rows_recorded`, the four-field token counts and the byte-category counters — so the
composition recompute and the billing-formula verification **are** script-derivable.

⛔ **But three things in the rendered report are NOT in the store:**

1. ⛔⛔ **The `**Total**` row is RENDER-TIME ONLY.** The TOON header carries `plan_id`, `updated`,
   `partial`, `unrecorded_phases`, `session_message_count` — **and no aggregate.** ⇒ The headline
   figure a human quotes, *and its `(n=5/6)` population qualifier*, exist **only in prose**. A script
   must re-sum and **re-derive the population itself**, and may legitimately pick a different one than
   the renderer did. ⭐ **That is two producers of one number with one of them unpersisted** — the
   `PLAN-TRUTH-049` shape, applied to the figure this epic quotes most often.
2. ⛔ **`inline_main_context_tokens` is SPARSELY persisted** — present in **1 of 6** phase blocks in
   the plan checked, while the operator's report showed it for five phases. ⇒ **A 3.45× cost gap
   visible in the report is not reconstructible from that plan's store.** (Measured: headline
   4,157,033 against inline 14,328,428.)
3. ⛔ **The disambiguating caveats are render-only** — *"excludes cache_read"*, *"not preferred —
   smaller than total_tokens under same-population max"*, *"Start is the latest entry only"*. These
   carry the **semantics that make the numbers safe to use**, and a script reading the TOON gets the
   values without them.

⇒ ⭐⭐ **This is exactly this plan's own subject one level up.** The plan was staged because *ledgers
disagree and the smallest is named actual*; here **the report and the store disagree about what
exists at all**, and the report wins because it is what anyone reads.

**Deliverable**: persist every figure the report renders — the aggregate Total **with its population
count as a field**, `inline_main_context_tokens` for every phase (or an explicit
`not_measured` marker, never absence), and the comparator/exclusion semantics as **data** rather than
prose. ⛔ **The renderer must derive 100% of its output from the store** — any figure it computes and
does not persist is a number nobody can check. ⚠ **Do not solve this by parsing `metrics.md`**; the
markdown is the artifact, not the source.

## ✅ ORDERING DECIDED 2026-08-08 — `PLAN-TRUTH-055` lands FIRST; this plan CONSUMES its vocabulary

`truthful-signals-040` § 2 confirmed the ownership split and left the order to us. **Decided and
answered as `code-intelligence-substrate-023`: their half first.**

- **They own the LABELLING half** — *which* population a Total names, as a **FIELD rather than a
  sentence** (folded into their `PLAN-TRUTH-055`, which owns the record shape underneath).
- **This plan owns the PERSISTENCE half** — the aggregate and its population qualifier must **EXIST in
  `metrics.toon`**, not only in the render. ⛔ They explicitly asked us **not** to cut it: *a renderer
  that computes a figure it does not persist has produced a number nobody can check.*
- ⛔ **NEITHER epic invents a second population enum.** Because `TRUTH-055` lands first, **it supplies
  the vocabulary and this plan writes into it.** ⇒ **D3 is a CONSUMER of that vocabulary, not a
  co-author** — if this plan finds itself defining permitted population values, it has taken the wrong
  half. ⚠ The one event that re-opens the question: `TRUTH-055` changing shape so it no longer supplies
  a vocabulary. They have been asked to tell us before it lands.

## Evidence Fold — 2026-08-08, from `lessons-handling-26-08-08-01-003` (cluster C08)

⚠ **The sender proposed three C08 members for this plan; TWO are folded here and ONE was re-routed.**
`2026-07-26-22-004` (310 of 1519 audit rows permanently pending by construction) is a **detector-population**
defect, not a token-ledger one, and went to `PLAN-CIS-016` instead. Recording the re-route so the
sender's suggestion is not silently overridden.

⛔ **NEITHER member adds a deliverable — both are instances of D3 (`every token figure carries its
population`), and that is the finding.** Two more producers of the same defect strengthens D3's case
without widening this plan, which already sits at the split-guard bar.

- **`2026-07-21-15-001` — `seconds_per_task` is computed from wall-clock, so it grades OPERATOR IDLE
  TIME as agent cost.** ⭐ This is D2's defect in a second field: a number whose name asserts one
  population (agent work) while its derivation covers another (elapsed time, operator included).
  ⛔ **Directly load-bearing for this epic**, because a wall-clock-derived cost figure is exactly the
  kind that gets cited as a token-reduction result. Any efficiency claim resting on `seconds_per_task`
  is population-mismatched at the source.
  - ⭐ **SIXTH CONSECUTIVE SIGHTING, AND IT IS ON OUR OWN PLAN** — read the lesson body, it is
    first-party and specific. PR #1084 (`content-search-seam`, PLAN-CIS-001):
    `seconds_per_task = 70744 / 7 = 10106`, the highest recorded, **11× the 900s warning threshold and
    composed almost entirely of one operator sleep cycle** (6-finalize's wall window is 55,221s of the
    70,744s total and contains a ~7.4-hour overnight gap). Recorded worked time for phases 2–5 is
    15,140s against 15,523s wall — **the plan's agent-side pace was unremarkable.**
  - ⛔⛔ **The same sighting carries a SECOND, independent defect that is squarely this plan's:
    `totals.duration_seconds` has NO honest value at all for 6-finalize, because that phase never
    closed its metrics boundary.** `metrics.toon` carries `[6-finalize] start_time` with **no
    `end_time`**, so any denominator for that phase is a **live-clock reading taken at whatever moment
    the retrospective happens to run — it would differ on every re-run of the same completed plan.**
    ⇒ **A figure that changes when you re-read it is not a measurement.** ⭐ This is the *mirror image*
    of the epic's standing finding that a closed phase row is never re-opened on loop-back — never
    closed, versus closed and re-entered — so **D4's reconciliation must handle both**, and the
    partiality labelling must be able to say *"boundary never closed"* distinctly from *"row absent"*.
  - ⛔ **Remedy constraint, stated by the lesson and binding: do NOT fix by clamping or by
    heuristically excluding long gaps.** The Worked figure is already recorded per phase; the ratio
    simply needs to read it. ⭐ The worked-duration fix also resolves the unclosed-boundary defect,
    because `agent_duration_ms` accumulates per dispatch and does not depend on the phase boundary
    closing.
  - ⚠ **Retirement ownership.** The lesson's *other* half (the calibration-anchors coverage gap) is
    **already closed** — cross-product table plus a both-directions set-equality test — and
    `PLAN-CIS-015`'s D5 line for it has been struck accordingly. **This plan owns the only open half,
    so this plan performs the lesson's retirement.**
- **`2026-08-03-16-001` — `cmd_enrich`'s persistence loop HARDCODES the four usage fields instead of
  deriving them from `_FOUR_FIELD_USAGE_LABELS`.** ⭐ **This is the mechanism behind a symptom this epic
  already owns**: a hardcoded field list cannot drift *visibly* — it silently omits any field added to
  the canonical label set, and the omission reads as a zero rather than as an absence. ⚠ Note the
  adjacency to the structurally-empty per-dispatch columns `truthful-signals` keeps (§ "What is NOT
  ours") — **the same four field names appear in both**. ⛔ **Do not merge the two**: theirs is
  *producers never populate the columns*, this is *the persister does not derive its field list from the
  canonical set*. Different fixes, and a merged item would ship one and claim both.

**Claim labels** — OBSERVED: lesson ids, components, categories, and the re-route decision above.
The numeric figures in the source cluster are quoted **as the lessons recorded them**, are NOT
re-derived here, and each carries its own unpublished population — do not cite any of them as a measured
result without re-deriving. HYPOTHESIS (verify-at-outline): that both instruments still misreport.
Confirm/refute artifacts: `manage-metrics`' `cmd_enrich` persistence loop against
`_FOUR_FIELD_USAGE_LABELS`; the `seconds_per_task` derivation site.

## ⭐⭐ A SECOND, LARGER LEDGER DISAGREEMENT — folded 2026-08-09 from inbox `self-review-resweeps-full-surface-every-round-009`

**OBSERVED first-party on PR #1126.** `metrics.md` publishes:

```text
| **Total** | **3h14m (n=4/6)** | ... | **2,392,836 (n=4/6)** | ... |
> Partial: unrecorded phases — 6-finalize
```

Meanwhile `work/metrics-dispatch-boundaries-6-finalize.toon` holds **12 rows totalling
2,507,354 tokens — MORE THAN THE ENTIRE PUBLISHED TOTAL.** The plan's real dispatched spend is
**4,900,190**, so the headline understates it by **51%**.

⭐ **This is the plan's own archetype at larger magnitude than the founding instance**, and the
data needed to close the gap was already on disk, written by `record-dispatch-boundary` during
the same phase.

**Root cause**: `generate`'s completeness verdict keys a phase's *recorded* status **solely off
`end_time`**. A phase that dispatched twelve times and recorded every one of them is still
"unrecorded" if its terminal close never fired — ⛔ **and the terminal close is the last thing a
finalize does, so `6-finalize` is simultaneously the phase most likely to be missing it and the
phase most likely to hold the largest figure.**

**Deliverable**: when a phase has no `end_time` but DOES have a
`metrics-dispatch-boundaries-{phase}.toon`, fold that file's row sum into the phase's `Tokens`
cell as a **labelled** figure — the same default-plus-exception labelling discipline the
`(inline)` / `(mixed)` markers already use, e.g. `(from dispatch boundaries)` — and mark the
Total accordingly. ⛔ **Keep the `partial` verdict for duration**, which the boundaries file
cannot supply honestly.

⭐ **Precedent in the same skill**: `enrich` already folds inline main-context tokens into a
zero-dispatch phase's `total_tokens` and labels the row `total_tokens_population: inline`.
This is the same move for the same reason, applied to the dispatched population.

⚠ **This is a USEFULNESS bug, not a truthfulness one** — the `(n=4/6)` marker is honest. But
every downstream consumer reads the total as a figure rather than a floor: the plan-efficiency
anchors score against `totals.tokens`, and on this plan the published figure would have scored
the run at roughly **half** its real cost against every ratio threshold. ⛔ **A partiality marker
that is technically correct and practically ignored is how a 2.5M-token phase disappears from a
cost review.**

⛔ **Adopt the renamed keys, do not the old ones**: `partial` / `unrecorded_phases` are renamed
to `any_phase_missing_end_time` / `phases_missing_end_time` by
`metrics-record-cannot-represent-re-entered-phase` **with no dual-key shim**, and archived
records still carry the old ones — so any read of an archived record needs the three-state read
(`current` / `old-schema` / `pre-#812`) with `old-schema` reported explicitly.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
