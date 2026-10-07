# Landing Analysis: PLAN-CIS-031 — Self-Review Re-Sweeps The Whole Surface Every Round At Flat Cost

epic: code-intelligence-substrate
workstream: WS-04
pr: 1126 — https://github.com/cuioss/plan-marshall/pull/1126

> Landing record for one shipped plan. Claims below were corroborated first-party against
> `git show --stat 72982d3d4`, the merged tree at HEAD, and `ci pr view --pr-number 1126`
> before being recorded. Two of the plan's own reported claims were checked and one of them
> **failed** — see § Follow-Ups item 1.

## Deliverable Fidelity vs Spec

Corroborated against the merge commit `72982d3d4` (19 files, +1553/−232) and by reading the
merged source, not from the plan's own report.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — GATE: re-derive the per-round cost curve first-party | shipped-as-specified | Verdict `confirmed`, population published **before** the curve (`distinct_plans_scanned=5`, `plans_with_at_least_one_round=3`, `plans_with_two_or_more_rounds=2`). No coefficient quoted, no saving claimed — both spec anti-goals honoured. |
| D2 — scope the re-run to the delta | shipped-as-specified | `ext-self-review-plan-marshall/scripts/self_review.py` (+115) takes a since-ref; round 1 and the final confirmation round keep the full sweep. |
| D2b — make a missing `head_at_completion` LOUD | shipped-as-specified | `manage-status/scripts/_cmd_mark_step.py` (+214) refuses a head-dependent terminal `done` with no anchor; new `test/plan-marshall/manage-status/test_mark_step_head_anchor.py` (+368) pins the refusal. This is the sharper risk the 08-08 re-grounding handed D2, and it landed as the deliverable. |
| D3 — sweep the CLASS before closing a round | shipped-as-specified | `phase-6-finalize/workflow/pre-submission-self-review.md` (+111), pinned by `test_pre_submission_self_review_verdict.py`. The obligation states its bound (surfaced candidates only) at the point it states the obligation. |
| D4 — report the detector mix per round | shipped-as-specified | `_self_review_patterns.py` (+103) carries a family per registry entry; tests assert totality and the partition sum. |
| D5 — loop-back ceiling at the admission boundary | shipped, **unexercised** | `phase-6-finalize/SKILL.md` (+77) consults before dispatching N+1, outside both knob branches, counter persisted. The run converged at round 6, so the ceiling never bound. Correct-by-review, unverified-in-anger. |
| D6 — recorded-footprint scoping + docs-only settlement | shipped-modified | `standards/pre-push-quality-gate.md` (+18). The premise D6 was authored against was **stale** — footprint-aware bundle derivation for the per-bundle arm had already landed — so D6 (a) records that landing and (b) settles only the genuinely-open question. This is § Structural Findings **F0 firing again**, this time caught inside the plan rather than at emit. |

Six deliverables, all fulfilled. The spec's § Anti-goals held: no round-count reduction, no
quantified saving, no weakened termination criterion.

## Metrics and Anomalies

- **Tokens**: `pre-submission-self-review` ran **six** rounds finding 5, 5, 2, 3, 4, 0 and
  consumed **1,528,196** tokens — **61% of `6-finalize`** and **31% of the plan** against a
  reconstructed dispatched total of **4,900,190**.
- ⛔ **The published headline is a 51% undercount.** `metrics.md` prints **2,392,836 `(n=4/6)`**
  because `6-finalize` never closed its row, while
  `work/metrics-dispatch-boundaries-6-finalize.toon` alone holds **2,507,354** across 12 rows —
  *more than the entire published total*. The partiality marker is honest and was ignored anyway.
  → folded to **PLAN-CIS-022**.
- **Duration**: 1-init 20:33Z → 6-finalize close 03:34Z ≈ **7h01m**, of which `6-finalize` is
  **3h16m**. `idle_duration_ms` on `6-finalize` is 5,052,516 ms (84 min) — an unattended run.
- **Anomalies**: `5-execute` re-entered (`close_count: 2`), so every `5-execute` figure on this
  plan is subject to `PLAN-TRUTH-055`'s re-entered-row rule and is **labelled, not quoted**.

### ⭐⭐ First-party recompute — the composition claim confirmed a THIRD time

Recomputed by the orchestrator from `work/metrics.toon` over all six phase blocks, using
`input + output + 1.25·cache_creation + 0.1·cache_read`:

| component | raw tokens | billing weight | share |
|---|---:|---:|---:|
| `cache_read` | 842,558,977 | 84,255,898 | **77.40%** |
| `cache_creation` | 18,876,879 | 23,596,099 | 21.68% |
| `output` | 1,002,375 | 1,002,375 | **0.92%** |
| `input` | 6,317 | 6,317 | 0.006% |

Recomputed total **108,860,688** against the file's own published per-phase sum
**108,860,690** — a two-token delta (rounding). ⇒ **Context is 99.08% of billing weight;
generation is 0.92%.** The formula and the composition are now verified on three independent
plans (this one, `plan-45`, and `truthful-signals`' n=47). ⚠ Scope unchanged: this corroborates
the **composition**; the per-phase **ranking** stays retired.

### ⭐⭐⭐ The decomposition this plan's data makes available for the first time

`cache_read / tool_uses` yields the average **resident context** per API call, and the phase
row already carries the **turn** count. Cost is their product, and both factors are actionable
where the single number was not:

| phase | billing | share | resident ctx | turns | `cache_creation` as % of phase |
|---|---:|---:|---:|---:|---:|
| 1-init | 1.01M | 0.9% | ~252K | 37 | 6.4% |
| 2-refine | 3.06M | 2.8% | 237K | 94 | 25.0% |
| 3-outline | 11.72M | 10.8% | 359K | 244 | 23.8% |
| 4-plan | 11.20M | 10.3% | 273K | 140 | **65.4%** |
| 5-execute ⚠ | 28.36M | 26.1% | **696K** | 365 | 9.8% |
| 6-finalize | 53.50M | 49.2% | **721K** | 598 | 18.4% |

Two results, both new:

1. **The average byte is re-read ~44.6 times** (842.6M read / 18.9M created). ⇒ the marginal cost
   of a byte is `1.25 + 0.1·(turns_remaining)`, i.e. **~5.7× at the observed mean and ~13.4× for a
   byte entering early in `5-execute`'s ~122-turn envelope.** **When a byte enters dominates how
   big it is** — and envelope length is a variable nothing in this epic owns. → **PLAN-CIS-040**.
2. **`4-plan` is structurally inverted**: 65.4% of its billing weight is cache *creation*, against
   6–25% everywhere else, at a read/creation ratio of 6.5 versus 36–180 elsewhere. Unowned. → filed
   as an Open Defect and scoped into **PLAN-CIS-042** D3.

### ⭐⭐ The exploration split, on all six phases — PLAN-CIS-036's gate is now satisfiable

| phase | exploration % of tool-result bytes | index-answerable | doc-residency | unattributed |
|---|---:|---:|---:|---:|
| 2-refine | 80.5% | **3.3%** | 90.7% | 6.0% |
| 3-outline | 78.4% | 16.8% | 73.0% | 10.2% |
| 4-plan | 80.2% | **0.0%** | 43.9% | 56.1% |
| 5-execute ⚠ | 82.2% | **33.6%** | 59.5% | 6.9% |
| 6-finalize | 74.2% | 13.8% | 64.5% | 21.6% |
| **whole plan** | ~77% | **15.9%** | **65.2%** | 18.9% |

⛔⛔ **PLAN-CIS-036's central hypothesis is HALF-CONFIRMED AND HALF-REFUTED, and the refuted half
is the load-bearing one.** The spec predicted `6-finalize` was the doc-residency **worst case** and
that `2-refine` and `5-execute` would look better. `5-execute` does — 33.6%, the best case in the
plan. **`2-refine` is the WORST phase in the plan at 3.3% index-answerable / 90.7% doc-residency**,
and `6-finalize` is not the worst case at all: two phases are worse.

⭐ **The epic's addressable share on this plan is 15.9%** — 2.3× the 7.0% that alarmed the epic at
#1086, still an order of magnitude below the roadmap premise. **The largest bucket by 4× is
doc-residency at 65.2%.** Multiplying through (exploration ≈77% of tool-result bytes × 65.2%):
**roughly half of all tool-result bytes are plan-marshall reading its own skills, standards and
workflow docs.** → **PLAN-CIS-039** (new WS-06).

⛔ **And the two `unattributed` numbers are not the same number.** Unattributed *bytes* are 18.9%;
`cache_read_unattributed` is **65.9% of all cache_read** and ≥83% in every phase except
`6-finalize` (40.5%). PLAN-CIS-030 D2's reconciliation identity holds exactly — verified here on
`6-finalize`, 136,811,943 + 7,731,849 + 66,732,634 + 45,218,522 + 0 + 174,503,179 =
430,998,127 = `cache_read_input_tokens` — **because `unattributed` is a catch-all**. ⇒ **the
instrument attributes well only in the phase it was built and tested against**, which is this
epic's own signature archetype landing on the instrument for the second time. → **PLAN-CIS-042**.

## Routing and Merge Behavior

- **Review: effectively zero, and the three outcomes are three different failures.**
  - `pr-agent` — participated, raised 2 focus areas, **both refuted against live code**. The
    "Scoping Bug" rested on a premise `_resolve_footprint`'s own typed two-state contract
    contradicts, and its suggested guard would have been **vacuous with an unreachable `else`**,
    turning a documented fail-safe into a fail-quiet clean verdict. The "Unhandled Exception" area
    named three already-handled classes and one (`YAMLError`) that cannot occur — no YAML library
    exists in that read path.
  - `CodeRabbit` — genuine rate limit, **never awaited**.
  - `Sourcery` — refused on a **diff-size cap of 150,000 characters**.
  - ⛔ **A size cap is not a rate limit**: waiting clears a rate window and never clears a size cap.
    Second sighting of the mechanism; routed to `review-apparatus` (their `-009` carries the first).
- **CI/merge**: squash-merged through the platform merge queue at `72982d3d4`. No rebase conflicts.
  No surface collision observed — the plan ran alone (`R=1`).
- ⛔ **19 Q-Gate findings reached merge at `resolution: pending`.** No real defect shipped — the
  fixes landed, only the records stayed pending — but the blocking gate never evaluated them:
  `handshakes.toon` carries no `6-finalize` row and `_BLOCKING_BOUNDARIES` is exactly
  `{6-finalize}`. → **PLAN-CIS-044**.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-CIS-031 --status shipped`
- [x] row `pr` stamped `1126`
- [x] row `landing` stamped `landings/PLAN-CIS-031.md`
- [x] row `plan_marshall_plan_id` stamped `self-review-resweeps-full-surface-every-round` —
      **probed, not guessed**: `ci pr view --pr-number 1126` returns head branch
      `feature/self-review-resweeps-full-surface-every-round`, and the archived plan directory is
      `2026-08-09-self-review-resweeps-full-surface-every-round`.
- [x] epic.md queue reconciled from status.json
- [x] Open Defects added: the `4-plan` creation inversion; the `error`-conflation that undermines
      PLAN-CIS-035's headline; the `scope_searched` requirement that arrived mid-run and was never
      applied
- [x] `PLAN-CIS-036`'s hard gate released — the post-`9b689d65b` population is now **n=5** archived
      plans carrying `work/metrics.toon`, at least one with all six phases
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

1. ⛔⛔ **A message that would have changed this plan's deliverables sat unread in the epic inbox
   for the plan's entire run.** `review-apparatus-006.md` (created 2026-08-08T20:56Z, 23 minutes
   after this plan's `1-init` began) carried a hard requirement — *"every residual/absence claim
   must publish `scope_searched` + `files_scanned`"* — with the reasoning that this
   *"converts your scoping change from a risk into a safe one"*. **Verified first-party at HEAD:
   neither token appears anywhere in `self_review.py` or `pre-submission-self-review.md`.** The
   delta scoping shipped **without** the claim-scope publication that makes it safe.
   ⇒ ⭐ **The structural lesson is about the inbox, not the plan**: a mid-run message has no reader.
   The drain is an orchestrator-tier act that runs between plans, so a message aimed at a running
   plan is architecturally undeliverable. Recorded as an Open Defect. → **PLAN-CIS-043** D3.
2. ⛔⛔ **PLAN-CIS-035's headline premise is REFUTED by this landing.** Its D1 rests on *"32% of
   6-finalize dispatch spend went to dispatches terminating in `error` or `blocked_session_restart`"*
   read as spend that **produced nothing**. On this plan **five of six `error`-stamped self-review
   rounds found 5/5/2/3/4 defects and returned for a loop-back** — they are the plan's most
   productive dispatches. `DISPATCH_TERMINATION_CAUSES` has no member for *returned with findings*,
   so a successful review round is stamped with the token reserved for a fatal crash. ⇒ **`error` is
   not a proxy for "produced nothing", and CIS-035 must re-derive its denominator before scoping.**
   Folded onto CIS-035 as a premise correction.
3. `[DISPATCH]` undercounts the plan's most expensive step **6:1** (six spawns, one line) —
   emission is wired to first entry, not to the loop-back re-fire. → folded to **PLAN-CIS-011**.
4. `_detect_count_prose` opens only `SKILL.md` while its sibling `_collect_skill_contract_sources`
   globs `standards/*.md` — **verified at HEAD** (`_self_review_detectors.py:1070` vs `:276-279`).
   A stale count in a `standards/*.md` doc is invisible to every round, delta or full. → **PLAN-CIS-043**.
5. `duplicate_claimable_keys` / `discard_without_report` carry `in_total: true` with **no consuming
   check** — volume-read-as-coverage inside the contract that exists to detect it. Carries an
   epic-level policy call (the two remedies move the published count in opposite directions) →
   recorded under § Open Decisions; mechanism → **PLAN-CIS-043**.
6. `check-routing-decisions --diff-file` reports a vacuous `skip` on the plan-relative form its own
   SKILL.md documents, hiding a real `mis_prune:sonar-roundtrip` failure. → folded to **PLAN-CIS-019**.
7. Post-merge footprint resolution from the landing commit (`git show --name-only --pretty=format:`
   verified to return the 19 paths for `72982d3d4`). → folded to **PLAN-CIS-034** D4, which already
   owns the merge-commit fallback tier.
8. `references.affected_files` declared **14** against a realized **19** — the recurring
   under-declaration archetype, fifth sighting.
