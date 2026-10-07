# PLAN-TRUTH-035: the token `Total` is a partition labelled a whole — across four populations, three of them mislabelled

epic: truthful-signals
workstream: WS-01

## Objective

`metrics.md` renders one row called **`Total`**. It is not a total of anything coherent. Verified
first-party against `.plan/local/archived-plans/2026-08-02-barrier-override-not-head-bound/`
(`metrics.md`, `work/metrics.toon`, `work/metrics-dispatch-boundaries-6-finalize.toon`) — every figure
below was re-derived, not taken on report.

## OBSERVED — the four populations, per phase

| Phase | `total_tokens` (rendered as **Total**) | `subagent_total_tokens` | `dispatch_boundary_total` | `inline_main_context_tokens` | samples | `billing_weighted_total` |
|---|---|---|---|---|---|---|
| 1-init | **41,003** | **0** | — | *(absent)* | **0** | 720,319 |
| 2-refine | 226,454 | 226,454 | — | 585,566 | 1 | 2,528,960 |
| 3-outline | 535,346 | 535,346 | — | 1,116,295 | 3 | 6,104,993 |
| 4-plan | **439,628** | **577,452** | 211,852 | 2,149,438 | 3 | 7,268,957 |
| 5-execute | 466,370 | 466,370 | 304,879 | 1,990,349 | 4 | 12,422,999 |
| 6-finalize | 2,426,526 | 2,426,526 | **770,036** | 7,514,102 | **16** | 37,430,093 |
| **SUM** | **4,135,327** | **4,232,148** | 1,286,767 | **13,355,750** | | **66,476,321** |

## ⛔ Three defects the originating finding did NOT report

### 1. The `Total` row sums TWO DIFFERENT POPULATIONS

**1-init has `subagent_total_tokens: 0` and `subagent_samples: 0`**, yet contributes **41,003** to the
`Total`. That 41,003 is exactly `input 88 + output 16,012 + cache_creation 24,903` — **main-context
tokens**. And 1-init is the one phase with **no `inline_main_context_tokens` field at all**.

⇒ When a phase dispatches nothing, `total_tokens` **silently falls back to the main-context figure**
instead of reporting 0. The `Total` is therefore *dispatched for five phases plus main-context for one*.
⭐ **The originating finding's own framing — "counts dispatched subagent tokens only" — is itself wrong**,
in the same confident direction as the artifact it criticises.

### 2. The stated "same-population max" rule is applied to ONE of TWO competing measures

`metrics.md` says of `dispatch_boundary_total`: *"recorded; not preferred — smaller than total_tokens
under same-population max"*. But at **4-plan**, `subagent_total_tokens` (**577,452**) is **LARGER** than
the rendered `total_tokens` (**439,628**) — and metrics.md never shows it. ⇒ Under the document's own
stated rule the 4-plan figure should be 577,452 and the `Total` **4,232,148**. The max rule is enforced
against the smaller competitor and skipped against the larger one.

### 3. ⭐⭐ `dispatch_boundary_total` is a 37.5%-COMPLETE SAMPLE described as a same-population total

`work/metrics-dispatch-boundaries-6-finalize.toon` contains **6 rows** (summing to exactly 770,036)
while `metrics.toon` records **`subagent_samples: 16`** for the same phase.

⇒ **The ledger captured 6 of 16 dispatches.** It is not "the same population measured smaller" — it is a
**different, partial population**, and the parenthetical that explains the 3.2× gap does so with a
**false premise**. ⛔ This is the epic's archetype at its purest: *the discrepancy was noticed, named, and
explained away*. An unexplained gap invites investigation; a confidently explained one closes it.

## ⛔ The framing that matters most to the operator

The operator asked **"why did this cost so much?"**. The document renders **three work-comparable
numbers** and dismisses the one cost number in its own parenthetical as *"not a work-comparable
measure"*. That dismissal is **correct about work and useless about cost**: `cache_read` is 281,441,646
tokens in finalize alone, and it is billed.

⇒ **There is no cost figure in the cost report.** For "how much did this cost", every rendered number is
the wrong one and the right one carries a warning label against using it. ⭐ **The fix is not arithmetic
— it is that a work measure and a cost measure are different questions and the report answers only one.**

## Scale anchor — OBSERVED, for calibration

Shipped diff **9 files, +2,083 / −16**, of which **1,417 lines (68%) are tests**. Against that:
4,135,327 dispatched · 13,355,750 inline · **66,476,321 billing-weighted**. 5-execute — the phase that
produced the change — is **11%** of dispatched spend; 6-finalize is **59%**.

## Deliverables

1. **D0 — GATE: derive the population lattice.** Enumerate every token field `metrics.toon` records,
   what each measures, and which are disjoint. ⛔ **Both directions**: fields rendered without a
   population label, AND fields recorded but never rendered (`subagent_total_tokens` is the proof case).
2. **D1 — make every rendered figure name its population.** `Total (dispatched)` etc. ⛔ **Do NOT sum
   dispatched + inline into a new headline** — they are measured differently, and the originating
   finding's own "excludes 76%" headline performs exactly the addition its next paragraph forbids.
   **Do not inherit that error.**
3. **D2 — fix the zero-dispatch fallback** (defect 1). A phase with `subagent_samples: 0` must report
   `0` dispatched, not silently substitute main-context. ⚠ Check whether other consumers depend on the
   fallback before removing it.
4. **D3 — make partial ledgers say so.** `dispatch_boundary_total` must carry `rows_recorded` vs
   `subagent_samples` and be labelled **partial** whenever they differ. ⛔ Remove the "same-population"
   parenthetical — it is false. Resolve defect 2 by applying the max rule to **all** competing measures
   or to none.
5. **D4 — surface a cost figure as first-class.** `billing_weighted_total` is the only number answering
   the operator's actual question; it must stop being rendered as a disclaimer. **Keep the
   work/cost distinction explicit** — the failure is conflation, and merging them reproduces it.
6. **D5 — recalibrate the budget anchor to the population it measures.** `plan-retrospective` compared
   2,967,497 (a *mid-finalize* subtotal) against a 1.3M error anchor → 2.3×. Final dispatched is
   4,135,327 (3.2×). ⛔ **Every budget verdict this project has issued is computed against a partition**,
   so the anchor is calibrated to a number that omits the dominant cost. D5 is why this is not cosmetic.
7. **D6 — tests, each verified to FAIL pre-fix.** (a) A zero-dispatch phase reports 0, not main-context.
   (b) A dispatch-boundary ledger with fewer rows than `subagent_samples` is labelled partial.
   (c) Every rendered token figure carries a population label. (d) The population enumeration from D0 is
   asserted non-empty and contains `subagent_total_tokens` (the recorded-but-never-rendered case).

⚠ **Seven deliverables — over the ~6 scope-bloat threshold.** Split evaluated and **declined with
rationale**: D0 gates all of D1–D5, and D1/D3 are the same edit at two call sites. **D5 is the split
point if one is forced** — it is the only consumer-side deliverable and could stand alone once D0 lands.

## Claim Labels

- **OBSERVED**: every number in the population table, re-derived from `work/metrics.toon`.
- **OBSERVED**: the six dispatch-boundary rows summing to 770,036 against `subagent_samples: 16`.
- **OBSERVED**: 1-init's `41,003 = 88 + 16,012 + 24,903`, `subagent_total_tokens: 0`, no inline field.
- **OBSERVED**: billing-weighted per-phase figures summing to exactly 66,476,321.
- ⛔ **NOT VERIFIED — the originating finding's per-step finalize breakdown** ("self-review ×3 + fix ×2 =
  1,040,087 · review-bot machinery = 504,514 · lessons = 270,864 · retrospectives = 265,106 · create-pr
  = 151,835 · simplify = 143,200 · plugin-doctor = 50,920", claimed "exact from
  `work/metrics-accumulator-6-finalize.toon`"). **That file contains 8 scalar lines and no per-step
  rows**; the dispatch-boundary file has 6 unnamed rows. ⇒ **The breakdown is not re-derivable from
  either cited artifact.** Individual figures match rows (219,484 = the `error` row; 151,835; 143,200;
  50,920) but the step *attribution* and the 212,423 second self-review run are unsourced. **Treat as a
  lead; re-derive at D0 before any remedy is sized from it.**
- ⛔ **NOT VERIFIED — "96,985 tokens, zero output"**. The `blocked_session_restart` row does read 96,985,
  but **every row in that file has `output_tokens: 0`** — the column is uniformly zero, so it is not
  evidence of a zero-output kill. The waste claim may still be true; this artifact does not establish it.
- **HYPOTHESIS**: the zero-dispatch fallback affects other plans' 1-init figures identically.
  **DERIVE over the archived corpus at D0** — this is n=1.
- **Verify-first clause**: D2 assumes no consumer depends on the fallback. Confirm against every reader
  of `total_tokens` before changing it.

## Expected Surface

- **OBSERVED**: `manage-metrics` — `metrics.toon` field set, the `Total` renderer, the parentheticals
- **HYPOTHESIS**: the dispatch-boundary recorder (why 6 of 16 dispatches were captured)
- **HYPOTHESIS**: `plan-retrospective` / `audit-archived-plan-retrospectives` — the budget anchor (D5)

## Dependencies and Sequencing

- ⚠ **Surface-adjacent to `PLAN-TRUTH-027`** (build-ledger as the build-time oracle) — both touch the
  retrospective's measurement consumers. **Sequence, do not pair.**
- ⚠ **`PLAN-TRUTH-012`** touches `manage-metrics` SKILL.md. Re-ground if it lands first.
- ⚠ **Routing tension recorded**: by the three-way rule, measurement of our own runs is
  `code-intelligence-substrate`'s subject. It is kept here because the defect is **label-vs-content**,
  this epic's flagship archetype, and because D5 makes it a truth defect rather than a metrics feature.
  **Notify them on landing.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-035-the-token-total-is-a-partition-labelled-a-whole.md"
```

## ⛔⛔ FOLDED 2026-08-02 — a FOURTH population defect, and it is bigger than the other three

**From `review-apparatus-015` item 2**, first-party on PR #1078:

> `metrics.toon` closed `[5-execute]` once at 07:30:13 with `total_tokens: 162906`. The plan then looped
> back `6-finalize → 5-execute` **three more times**, each with an explicit `[MANAGE-STATUS]` transition
> in `work.log`, spending a further **758,059 tokens**. **No phase row absorbed them.**

| Source | Total |
|---|---:|
| `metrics.md` as generated | 1,571,619 |
| Reconstructed floor | **4,077,004** |

⇒ **61% of that run's spend is absent from the report**, and the `5-execute` row is presented as closed,
complete and authoritative at `162,906` while being an **82% under-count** of that phase's real `920,965`.

⛔⛔ **The partiality contract keys "recorded" solely off the presence of an `end_time`. A phase that was
closed and then RE-ENTERED has an `end_time`, so it passes the completeness test while being wrong** —
and the marker named only `6-finalize`. **The incompleteness marker under-reports its own
incompleteness.** That is this plan's thesis, one layer deeper than D0 was scoped for.

⚠ Also: `work/metrics-accumulator-5-execute.toon` reads `total_tokens: 0, tool_uses: 0, samples: 1`
despite six recorded dispatch boundaries — **the fallback path would have contributed nothing either.**

⇒ **D0's population must include phase-row re-entry**, and **D6 gains a test**: a phase closed and
re-entered reports the sum of all entries, and the partiality marker names it.

## ⛔ CONSEQUENCE FOR THIS ORCHESTRATOR'S OWN n=47 CORPUS — recorded, not hidden

Our corpus is parsed from `work/metrics.toon` **phase rows**. If closed rows systematically omit
loop-back re-entries, **every looping plan is under-counted**.

⭐ **Direction, derived rather than asserted**: a loop-back re-enters an EARLIER phase (`6-finalize →
5-execute`), so the omitted tokens belong to **5-execute**. ⇒ **our published `6-finalize 49.4% of
cache_read` is an OVER-estimate of finalize's share** — unless finalize rows are re-entered and lost the
same way, which is unknown. ⛔ **The phase shares are NOT settled and must not carry a sequencing
decision.**

⚠ **What is more robust, and why — stated so it is not over-claimed either**: the billing *composition*
(`cache_read` 76.1% / `cache_creation` 22.8% / `output` 1.1%) is a ratio over components that a missing
row drops **together**, so it survives unless missing rows differ in composition from present ones.
**Plausible, unverified.** ⇒ **The "99% of cost is context" conclusion is the more durable one; the
per-phase ranking is the fragile one.**

## ⚠ FOLDED — `--termination-cause` is missing a member, so a working gate reads as a failure

**From `review-apparatus-015` item 3** (SECOND sighting): the documented enum lists 6; the shipped
argparse accepts **11**, and SKILL.md says unrecognised values *"are rejected as script errors (there is
no implicit fallback)"* — which makes the omission read as a **prohibition** rather than a gap.

⭐ **The genuinely new half**: there is **no value meaning "the step completed successfully and returned
a loop-back."** So three `pre-submission-self-review` passes — **each of which found a genuine defect,
i.e. the gate working exactly as designed** — were stamped `error`. ⇒ **Any consumer computing an error
rate over this file reads 27% error on a run whose finalize had zero step failures.**

⚠ **The enum lacks a member, not just docs.** ⛔ **Evaluate a split at outline** — this is the same skill
and the same archetype but a different mechanism from the token populations.

## ⛔⛔ ARRIVED AFTER LAUNCH — 2026-08-03, from PLAN-TRUTH-010 / PR #1082

⚠ **This plan was already RUNNING when this evidence landed.** It is appended, not woven in — treat it
as a finding to reconcile at outline, not as part of the brief the run started from.

### 1. THREE totals for one plan, from three producers, none labelled with its population

| Source | Total |
|---|---|
| `metrics.md` (published artifact) | **2,782,409** |
| Retrospective reconstruction (published + the on-disk `metrics-accumulator-6-finalize.toon`) | **≈5,468,970** |
| `record-metrics` step / operator report | **6.2M** (finalize 2.9M, 2.2× execute) |

⭐ The third is **not** the second: `record-metrics` runs at finalize order 18, **after** the
retrospective, so it sees a phase row the retrospective could not. ⇒ **The producer's own number moves
depending on when you ask it.**

⇒ **This WIDENS the plan's thesis.** It is not one artifact being partial — it is **three artifacts
partitioning one run differently, with no field stating which population each covers.** The four
mislabelled populations in the title are within one file; this is the same defect **across** files.
⛔ Evaluate at outline whether the deliverable set must grow to cover cross-artifact reconciliation, or
whether that is a separate plan. **Do not silently absorb it — this plan is already at scope.**

### 2. ⛔ MY PREDICTED ERROR DIRECTION WAS WRONG — correcting it here

The § above states our `6-finalize 49.4%` is an **OVER**-estimate, reasoning that a loop-back re-enters
an *earlier* phase so the omitted tokens belong to 5-execute.

**Observed here: the opposite.** `metrics.md` carried `> Partial: unrecorded phases — 6-finalize` and a
**blank 6-finalize row**, while `work/metrics-accumulator-6-finalize.toon` — same subsystem, present on
disk — already held `total_tokens: 2,686,561` (16 samples, 612 tool_uses). **The largest phase was
dropped whole**, so this plan's corpus contribution **UNDER**-states finalize.

⇒ ⛔⛔ **The error direction is not uniform across plans.** It depends on *where the run stopped relative
to each row's close*, which varies per plan. **The n=47 per-phase ranking therefore cannot be repaired
by adjustment — it must be re-derived.** ⭐ **The earlier reasoning was not wrong about the mechanism, it
was wrong to generalise one mechanism into a direction.** Both mechanisms are live simultaneously.

✅ **Unchanged**: the billing *composition* argument still holds — a dropped row omits all components
together. **"99% of cost is context" remains the durable conclusion.**

### 3. The concrete remedy the filer proposes for the blank-row case

When a phase row lacks `end_time` but `metrics-accumulator-{phase}.toon` **exists**, fold the accumulator
in as a **provisional** figure with an explicit marker, instead of rendering the phase blank.
⭐ *"A provisional 2.69M is far closer to the truth than a blank, and the marker keeps it honest."*
⚠ **Confirm the accumulator is authoritative-enough before adopting this** — a provisional number that is
itself a partition would reproduce the defect one layer down.

## ⭐⭐ 2026-08-03 — the MECHANISM behind the three totals, from `code-intelligence-substrate`

Probed on merged main after PR #1080: **`plan-retrospective` = `order: 995`; `record-metrics` =
`order: 998`.**

⇒ **995 < 998 — the retrospective reads `metrics.md` BEFORE `record-metrics` writes it.** #1080's change
to `record-metrics` was a single line (`post_run_review: true`) and **does not close the accumulator
first**.

⭐ **This is not new evidence, it is the EXPLANATION** for the three-totals table above: the published
figure, the retrospective's reconstruction and `record-metrics`' own total differ **because they sample
at three different points in a sequence whose ordering nobody declared.** ⇒ ⛔ **The plan's remedy must
address the SAMPLING POINT, not only the labelling.** Labelling each artifact with its population is
necessary; it does not make the retrospective's number correct.

⚠ **The sibling's honest qualifier, adopted**: the partiality machinery still labels the gap, so the
retrospective's figure is an **honest floor**, not a false total. ⛔ **But an honest floor consumed as a
total is still a wrong decision input** — and the operator report quoted 6.2M while the artifact said
2.78M.

⭐ **Systematic, not incidental** — corroborated first-party on #1080: that run's
`pre-submission-self-review` looped **13 times** across three loop-back waves, and its `6-finalize`
(5.6M) outspent `5-execute`. ⇒ **A plan whose execute phase is re-entered several times is the NORMAL
shape of a plan-marshall run.**

⛔ **Standing rule adopted from their lesson `2026-08-03-06-004` — directly relevant to this plan's
verification**: *when diagnosing a run, read the step order from the run's own manifest or step log,
**never from the tree the run produced**.* They briefly refuted a sibling's stale-cache diagnosis by
reading post-merge `main`'s orders, which were the orders #1080 **installed**, not the orders that
**ran**. ⚠ **This plan will read archived trees constantly — the same trap applies to every phase row it
parses.**

## ⭐⭐ 2026-08-03 (`-016`) — a FOURTH total, and it is the dangerous magnitude

Independent instance on **#1080**, two producers, **one run**:

| Source | Total for `PLAN-CIS-028` / #1080 |
|---|---:|
| `plan-retrospective` (its own cost section) | **10.06M** |
| `record-metrics` (operator finalize report) | **10.4M** |

**≈340K apart — 3.4%.**

⛔⛔ **The small size is the finding, not a mitigation.** *"A 2.2× gap gets investigated; a 3.4% gap gets
quoted."* ⇒ **#1082's spread is the visible symptom; this is the population.** Any deliverable that only
catches gross disagreement leaves the common case untouched.

⭐ **It is exactly what the `995 < 998` mechanism predicts** — the two producers sample either side of
the accumulator close, so the earlier reader is short by whatever the later one still had to add.
⇒ **Second independent confirmation of the sampling-point mechanism, on a different PR and a different
epic's plan.** Neither figure is labelled with its population or its sampling point.

⚠ **Both figures are second-hand to us and one is second-hand to the sender** (the 10.06M is the
retrospective's self-report; the 10.4M is the operator's report of `record-metrics`). **Neither was
re-derived. Treat as a LEAD** — but the *mechanism* it corroborates is first-party on both sides.

## ⛔ A DRAIN-SURFACE GAP this exposes — wider than this plan

The sender flagged the **surface**, not just the items: *"the operator's finalize report is a different
surface from the inbox — it carries per-step outcomes and a `record-metrics` total that no inbox
message contains."*

⇒ ⛔ **This orchestrator's drains read inbox messages only.** Both items above, plus the
`0 removed, 0 promoted, 0 adapted, 180 retained` outcome folded into `PLAN-TRUTH-044`, live **only** in
the operator-facing report. **A per-step evidence channel exists that our drain does not see**, and we
have been treating inbox-drained as ingested.

⭐ **Our own archetype, on our own process**: *inbox count 0* is a confident signal that has stopped
tracking what it describes. **Recorded in the anchor as a standing practice** — when the operator pastes
a finalize report, it is a **distinct evidence surface** to mine, not a summary of the inbox.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
and the sole sanctioned write mechanism are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
