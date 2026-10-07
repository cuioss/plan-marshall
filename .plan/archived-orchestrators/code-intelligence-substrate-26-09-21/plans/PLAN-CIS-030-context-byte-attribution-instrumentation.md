# PLAN-CIS-030: `cache_read` Is Measured Per Phase And Attributed To Nothing

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-02 from `truthful-signals-027` (cross-epic token-reduction roadmap, lever **L3**),
> corroborated by `truthful-signals-025`. This spec is SELF-SUFFICIENT: the emitted command is a
> one-line pointer and carries no brief.

## Objective

`metrics.toon` records `cache_read` **per phase** and records tool-result bytes **per category**,
but nothing connects them: no artifact attributes a phase's `cache_read` to the bytes that caused
it. ⭐ **Every "reduce bytes entering context" lever in the fleet is therefore unsizeable and
unverifiable today** — including this epic's own flagship claim that a structured-answer substrate
replaces match-dump exploration.

Add the attribution: make it possible to say *which entering bytes are responsible for which
`cache_read` weight*, and reconcile the attributed total back to the phase total.

⛔ **This deliverable produces no savings itself.** It is the measurement prerequisite that makes
the savings claimable. Shipping the substrate levers before it means shipping changes whose effect
is unmeasurable — **this fleet's flagship archetype applied to its own optimisation programme.**

## Why this is ours

Measurement of our own runs — routing test 2. No PR/review surface, so it is not
`review-apparatus`'s. `truthful-signals` explicitly declines it as *"your subject, not mine"* and
routes it here as the one wave-1 item on their roadmap that **is not yet a plan on our side**.

## The measurement that motivates it (⚠ second-hand — re-derive before relying on it)

⚠ **Every figure below is `truthful-signals`' one pass by one reader over n=47 archived plans'
`work/metrics.toon`. It is a lead, not a fact. D1 re-derives it.** The billing formula is reported
to reconstruct exactly as `input + output + 1.25·cache_creation + 0.1·cache_read`.

| Component | Reported share of billing weight |
|---|---|
| `cache_read` | **76.1%** |
| `cache_creation` | 22.8% |
| `output` | **1.1%** |

⇒ ⭐⭐ **~99% of billing weight is context, not generation.** Every optimisation aimed at
"generate less" is aimed at ~1% of the cost.

Of tool-result bytes entering context (26 instrumented plans): **exploration 79.6%** · execute
18.2% · orchestration 1.6% · work 0.7%. Exploration is **76–85% of tool-result bytes in every phase
from 2-refine onward** — ⭐ including **6-finalize, which is the LARGEST exploration consumer**
(3,455 calls, ≈133/plan), refuting the intuition that finalize is script-heavy and
exploration-light. **There is no phase where the lever does not apply.**

**The compounding mechanism is the reason attribution is needed at all**: a byte enters once as
`cache_creation` (weight **1.25**) and is then re-read on **every subsequent turn** as `cache_read`
(weight **0.1**). ⇒ **The cost of a byte is a function of WHEN it enters context, not just its
size.** A per-phase total cannot express that; only per-byte attribution can.

## Deliverables

1. **D1 — GATE: re-derive the corpus measurement first-party (mutates nothing).** Re-parse
   `work/metrics.toon` across the archived corpus and confirm or refute the billing reconstruction
   and the four shares above. ⛔ **Do not build instrumentation on a second-hand number.** Report
   the re-derived figures with their population size, and state explicitly if the corpus has grown
   since n=47.
2. **D2 — attribute `cache_read` to causing bytes.** Emit a per-phase attribution that maps
   `cache_read` weight back to the entering byte-sources responsible for it. ⛔ **The attributed
   total MUST reconcile to the phase total** — an attribution that does not sum back is a second
   unverifiable number, not a fix for the first.
3. **D3 — separate index-answerable exploration from doc-residency.** ⛔ **This is a deliverable,
   not an assumption.** Part of the 79.6% is `Read` of workflow/standard documents required to
   execute a step, which a code substrate **cannot** remove (one observed plan read a ~1,400-line
   standard in four chunks to drive a merge that took three script calls). **The two need different
   fixes and only the first is this epic's.** Without the split, any saving attributed to the
   substrate is inflated by doc-residency it cannot touch.
4. **D4 — every emitted figure names its population.** A partial ledger is labelled partial; a
   figure derived from an incomplete marker set is labelled a floor. ⭐ This is the epic's
   fail-closed discipline (ADR-009) applied to its own instrument, and it is what stops D2 becoming
   the next confident-number-with-a-hidden-caveat.

Four deliverables — below the ~6 split-guard threshold, no split rationale owed.

## ⛔⛔ URGENT — the corpus D1 parses has a KNOWN SUBSTRATE DEFECT (folded 2026-08-03 from `truthful-signals-029` § 4)

**This changes the shape of D1's job and must be read before scoping it.** First-party on #1078 by
`review-apparatus`, forwarded here because it lands on the very rows D1 re-parses:

⛔ **A closed phase row is never re-opened on loop-back.** `[5-execute]` closed at **162,906**
tokens; the plan then looped back into it **three more times** for a further **758,059 tokens that
no phase row absorbed** — an **82% under-count** — while the partiality marker named only
`6-finalize`.

⭐ **The partiality contract keys "recorded" off the presence of an `end_time`, and a re-entered
phase HAS one — so it passes the completeness test while being wrong.** This is the epic's flagship
archetype living inside the instrument this plan exists to build.

⇒ **The n=47 figures in the table above are parsed from those rows.** D1 was already going to
re-derive them; **this is what it will find, and re-parsing the same rows more carefully will NOT
fix it** — the tokens are absent from the rows entirely and survive only in
`work/metrics-dispatch-boundaries-*.toon`. **D1 must therefore reconcile phase rows against the
dispatch-boundaries ledger, not merely re-read the phase rows.**

**What the sender believes survives — offered as their reasoning, NOT as a conclusion, and D1 must
settle it either way:**

| Figure | Status |
|---|---|
| **Composition** (`cache_read` 76.1% / `cache_creation` 22.8% / `output` 1.1%) | **likely durable** — a ratio over components a missing row drops *together*, so it holds unless missing rows differ in composition |
| **Per-phase ranking** (e.g. `6-finalize 49.4%`) | ⛔ **does NOT survive — and the ERROR DIRECTION IS NOT DERIVABLE** (see below) |

### ⛔⛔ CORRECTION 2026-08-03 — the sender WITHDREW their own direction claim. Do NOT encode a bias.

The version of this fold written hours earlier carried their prediction that loop-backs re-enter
*earlier* phases, so `6-finalize 49.4%` should be an **over**-estimate. **They withdrew it, unprompted,
on first-party evidence from #1082**: `metrics.md` published `total_tokens 2,782,409` with a **blank
`6-finalize` row** and the marker `> Partial: unrecorded phases — 6-finalize`, while
`work/metrics-accumulator-6-finalize.toon` — same subsystem, present on disk — already held
`total_tokens: 2,686,561`. **The largest phase was dropped WHOLE**, so that plan **under**-states
finalize.

⇒ ⛔ **TWO mechanisms are live simultaneously** — unabsorbed loop-back spend (under-counts the
re-entered phase) and whole-row omission at close (under-counts the omitted phase) — **and which
dominates depends on where a run stopped relative to each row's close, which varies per plan.**

⇒ ⛔⛔ **The per-phase ranking CANNOT be repaired by adjustment. D1 must RE-DERIVE it.** If any part
of this plan's scoping has encoded a correction factor or a known direction, **remove it** — a bias
correction applied to an error whose sign varies per plan is worse than no correction, because it
launders a suspect figure into a "corrected" one.

⭐ **And a third total exists for the same run**: `record-metrics` (which runs *after* the
retrospective) reported **6.2M**, against the published 2.78M and a reconstruction of ≈5.47M. **Three
producers, three totals, none labelled with its population.** The sender tracks that as
`PLAN-TRUTH-035` (running) — ⛔ **do not claim it**; but note their finding that our `995 < 998`
observation is the *mechanism* behind it: the three producers **sample at three points in a sequence
nobody declared.** ⇒ Labelling each artifact with its population is **necessary and not sufficient**;
the sampling point has to move too, and that half is `PLAN-CIS-034`'s.

⇒ ⭐ **Treat "~99% of billing weight is context" as durable and EVERY per-phase share as suspect.**
That asymmetry is itself a D4 obligation: the two classes of figure must not be reported with the
same confidence.

⭐ **Corroborated independently by this epic on PR #1080**: that run's `pre-submission-self-review`
looped **13 times** across three loop-back waves, and `6-finalize` outspent `5-execute`. A plan whose
execute phase is re-entered three times is not an edge case — **it is the normal shape of a
plan-marshall run**, which is what makes the under-count systematic rather than incidental.

## ⛔⛔ THE CORPUS SPANS AN EFFORT-LEVEL CHANGE — D1 MUST PARTITION ON IT (folded 2026-08-03, FIRST-PARTY)

**PR #1069 (`2d0229d1c`, merged 2026-07-30T19:51:10Z) raised the effort level of exactly the three
phases whose cost this plan measures.** Any share computed over the whole archived corpus is a
**blend of two configurations**, and reporting it as one number is this epic's own
partition-labelled-as-a-whole defect committed by its own instrument.

| Key | Before | After |
|---|---|---|
| `phase-3-outline.effort` | level-4 | **level-5** |
| `phase-5-execute.effort.default` | level-4 | **level-5** |
| `phase-5-execute.effort.verification-feedback` | level-3 | level-4 |
| `phase-6-finalize.effort.default` | level-3 | **level-5** (two levels) |
| `phase-6-finalize.effort.verification-feedback` | level-3 | **level-5** (two levels) |
| `phase-6-finalize.effort.post-run-review` | level-4 | **level-5** |

**Measured first-party by splitting the archived corpus at that instant**, using each plan's own
`[1-init] start_time` rather than its archive directory name — **39 before, 12 after, 0 spanning**:

| Metric (median) | before | after | ratio |
|---|---:|---:|---:|
| total | 3,090,553 | 4,152,537 | **1.34×** |
| 6-finalize | 1,489,376 | 2,068,989 | 1.39× |
| 5-execute | 518,577 | 920,106 | **1.77×** |
| 3-outline | 470,760 | 647,575 | 1.38× |

⭐ **Every raised phase rose and no unraised phase did**, which is what makes the attribution
credible rather than coincidental.

⚠ **CONFOUND, and it must be carried with the numbers**: the same commit also set
`phase-6-finalize.steps["default:lessons-capture"].lane` from `minimal` to **`off`**, removing a step
from finalize. That pushes finalize *down*, so **1.39× is if anything an UNDER-estimate** of the
effort effect there. `5-execute`'s 1.77× is the clean single-variable figure. ⛔ **Do not quote
"effort caused 1.39× on finalize"** — it is a two-variable cut.

**D1 obligation**: report every corpus figure **partitioned at `2026-07-30T19:51:10Z`**, with the
population size of each side, or state explicitly that the figure is configuration-invariant and why.

## ⭐⭐ AND THE RAISE PAID FOR ITSELF — the anti-goal this plan must protect (FIRST-PARTY, 2026-08-03)

⛔ **This is the single most important constraint on the whole token-reduction programme, and it was
measured, not argued.** The same partition, over `artifacts/findings/qgate-{phase}.jsonl`:

| Findings per plan (mean) | before | after | ratio |
|---|---:|---:|---:|
| 3-outline | 3.47 | 3.83 | 1.10× |
| 5-execute | 0.50 | 1.58 | **3.17×** |
| 6-finalize | 1.16 | 4.25 | **3.67×** |
| **all Q-Gate** | **5.13** | **9.67** | **1.88×** |
| PR-review (external) | 5.28 | 4.50 | **0.83×** |

⇒ ⭐⭐ **Cost rose 1.34× and internal defect yield rose 1.88×. Cost per Q-Gate finding FELL from
696,866 to 508,855 tokens — a 27% improvement in tokens-per-defect-found.** The more expensive
configuration is the *more* efficient one per unit of defect.

⭐ **Three corroborating signals, each of which would independently be weak and which together are
not:**

1. **Zero-yield runs collapsed.** `6-finalize` reported **zero** findings on **24 of 38** plans
   before (63%) and **2 of 12** after (17%); across all phases, `6 of 38 → 0 of 12`. ⇒ ⛔ **The old
   zeros look like under-examination, not cleanliness** — which is precisely this epic's flagship
   archetype (*a check that returns 0 from insufficient examination is indistinguishable from a clean
   pass*) sitting in our own quality gates the whole time.
2. **The resolution mix moved toward action.** Before: 60% `taken_into_account`, 34% `fixed`. After:
   **70% `fixed`, 30% `taken_into_account`**, with zero `accepted`/`pending`. ⇒ **If the extra effort
   were producing noise, the `fixed` SHARE would fall. It rose.**
3. **External yield fell as internal yield rose** — PR-review findings 5.28 → 4.50, and **4.18
   excluding #1080** (whose bot participation was degraded), so the drop is *stronger* without it.
   ⇒ A shift-left signature: defects are being caught earlier, not merely counted more.

⛔⛔ **ANTI-GOAL, BINDING ON THIS PLAN AND ON EVERY LEVER IT SIZES: lowering effort levels is NOT a
sanctioned token saving.** It is the one intervention now measured to *degrade defect detection
while improving the token number*, i.e. it would make this epic's own instrument report success for a
quality regression. Any lever whose mechanism reduces to "examine less" must be rejected on that
ground, not weighed against it. ⭐ **The legitimate target is bytes that buy nothing — redundant
exploration, re-read documents, unscoped re-sweeps — never examination depth.**

⚠ **Honest limits on the above, which D1 must not launder away**: n=12 after vs 39 before; the
periods differ in more than effort (`lessons-capture` lane, plan mix, subject difficulty); and the
per-plan internal-vs-external counts do **NOT** show a clean inverse correlation (two after-group
plans carry both high internal and high external yield). **The group-mean directions are the claim;
a per-plan trade-off is not.**

### ⛔⛔ CORRECTION 2026-08-03 — the first version of this fold SAMPLED its own population

**The figures above were first computed over three finding files named from memory —
`qgate-3-outline`, `qgate-5-execute`, `qgate-6-finalize` — out of SIXTEEN that exist.** The two
omitted were `qgate-2-refine.jsonl` and `qgate-4-plan.jsonl`: **the control group.** Re-run by
globbing the directory instead of naming it:

| Findings per plan (mean) | before | after | ratio |
|---|---:|---:|---:|
| **ALL findings (16 files)** | 26.15 | 43.92 | **1.68×** (was reported 1.88×) |
| all `qgate-*` | 6.08 | 11.17 | 1.84× |
| `pr-comment` (external) | 5.28 | 4.50 | 0.85× |

✅ **The headline and the anti-goal survive**: cost 1.34× against yield 1.68×, so cost-per-finding
still improves and the external drop still stands. **Three things must be corrected, and D1 inherits
all three:**

1. ⛔ **The resolution-mix "noise test" is MUCH weaker than reported.** Full population: `fixed`
   **29% → 36%**, not 34% → 70%. ⛔ **And 39% of before-period findings carry
   `resolution: <unset>`** (32% after) — so part of what looked like a behavioural shift toward
   action is an **instrumentation** shift in how resolutions were recorded. **The actioned-share test
   needs a reliably populated resolution field before it can discriminate anything; ours is not one.**
2. ⛔⛔ **A CONTROL PHASE'S YIELD ROSE.** Cost controls are clean (`1-init` 0.89×, `2-refine` 1.11×,
   `4-plan` 0.97× vs raised 1.38×/1.77×/1.39×), **but `4-plan` yield rose 1.73× with its effort
   unchanged and its cost flat**, while `2-refine` yield FELL to 0.54×. ⇒ **"The raise increased
   yield" is UNSETTLED at the per-phase level.** Something else moved finding counts in that window.
   What survives is the aggregate co-movement plus the clean **cost** control.
3. ⛔ **Per-phase attribution covers under a quarter of the corpus**: **1,176 of 1,547 findings carry
   NO `phase` field** (`<none>`). Any per-phase share is computed over a 24% subset that may not be
   representative — **D4 must label it as such, and D1 must not treat the phase-tagged subset as the
   population.**

### ✅ RE-VERIFIED 2026-08-03 — the zero-yield collapse HOLDS, with a control, and it rescues item 2

Re-run over the derived file population (phase from the record's `phase` field, falling back to the
`qgate-{phase}` filename):

| phase | status | zero-yield before | zero-yield after |
|---|---|---:|---:|
| 2-refine | **control** | 27/39 (69%) | 10/12 (**83%**) |
| 3-outline | RAISED | 7/39 (18%) | 0/12 (**0%**) |
| 4-plan | **control** | 21/39 (54%) | 7/12 (**58%**) |
| 5-execute | RAISED | 30/39 (77%) | 7/12 (**58%**) |
| 6-finalize | RAISED | 25/39 (64%) | 2/12 (**17%**) |

⭐ **Every raised phase's zero rate FELL; both controls' zero rates ROSE.** The original 24/38 → 2/12
reproduces at 25/39 → 2/12. **This is stronger than the withdrawn version — it has a control.**

⭐⭐ **AND IT EXPLAINS ITEM 2 ABOVE.** `4-plan`'s mean rose 1.73× **while its zero rate also rose**
(54% → 58%). Those are compatible only if the extra findings are **concentrated in a few plans** —
plan-difficulty variation, not a systematic effect. **The mean was contaminated by outliers; the zero
rate was not.**

⇒ ⛔ **D1 REPORTING RULE, and it is the most transferable thing this analysis produced: when testing
whether a detector's behaviour changed, prefer an outlier-robust COUNT statistic — the zero rate,
"on what fraction of runs did it report nothing?" — over a mean.** A mean over finding counts is
dominated by a handful of pathological runs and **will manufacture an effect in a control group**.
The zero rate answers the question the archetype actually poses. **A rising mean beside a rising zero
rate means the population is bimodal, and reporting only the mean hides it.**

⇒ **Item 2 is therefore reinstated ON THE ZERO-RATE STATISTIC and stays withdrawn on the mean.**
Item 1 (the resolution-mix noise test) and item 3 (the 24% phase-tagged subset) are **unchanged and
still binding**.

⭐ **Recorded as an instance of lesson `2026-08-03-06-002` committed by this epic's own analysis,
inside the very document that promotes the rule** — and it surfaced only because the operator asked
an unrelated question about a phase the list had omitted. **No part of the method caught it.**

## ⛔⛔⛔ ARRIVED 2026-08-03 WHILE THIS PLAN WAS ALREADY AT 6-FINALIZE — READ BEFORE TRUSTING ITS D1 OUTPUT

**`truthful-signals-038`, first-party from `PLAN-TRUTH-035` / #1083 (`3a20814b1`). This is a hard
precondition on D1 that arrived TOO LATE TO GATE THE RUN.** Whatever per-phase figures this plan's D1
produced were derived over a store that **cannot arithmetically represent a re-entered phase.**

From that plan's own `work/metrics.toon`:

```toon
[5-execute]
  end_time - start_time = 37m41s      duration_seconds: 41973.0   # 11h39m
  total_tokens: 1961416               tool_uses: 0   agent_duration_ms: 0
  close_count: 3
```

⛔ **Across the third close, `total_tokens` ACCUMULATED (+37,777) while `tool_uses` and
`agent_duration_ms` were REPLACED with the closing call's zeros.** Two fields in one row updated under
opposite semantics. And `metrics.md` rendered that phase with **`Start: 09:22:33Z`, `End: 07:05:28Z`
— ending 2h17m before it starts** — while `partial: false` **certifies the row**, because the
completeness contract keys "recorded" off an `end_time` a re-entered phase already has.

⇒ ⛔⛔ **The corpus problem is no longer "rows are missing". It is "re-entered rows are arithmetically
impossible".** And by this epic's own #1080 evidence (13 self-review loops, three `5-execute`
re-entries), **`close_count > 1` is the NORMAL shape of a plan-marshall run, not an exception.**

**Consequences, in order of what a reader must do:**

1. ⛔ **Any per-phase share this plan's D1 emitted is RETIRED AS EVIDENCE until re-derived — not
   adjusted, not caveated.** If the landing reports one, the landing analysis must label it
   accordingly rather than record it as a result.
2. ⛔ **`PLAN-TRUTH-055` (their side) is an explicit precondition of L3's per-phase re-derivation.**
   Do not schedule that re-derivation ahead of it: re-deriving from rows that cannot be true produces
   a result that **looks authoritative**, which is strictly worse than no result.
3. ✅ **What survives is the claim the whole roadmap rests on**: the **billing composition**
   (`cache_read` / `cache_creation` / `output`) is a ratio over components a corrupted row distorts
   **together** ⇒ **"~99% of cost is context" holds.**
4. ⛔⛔ **The four per-dispatch token columns are structurally empty.** `record-dispatch-boundary`
   persists `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`
   as *"the per-DISPATCH counterpart to the per-PHASE four-field view"*, and across **19 rows in three
   ledgers they are `0` on all four — uniformly, not sparsely.** Every producer omits the flags; they
   default to `0` and **persist as though measured**. `cache_read: 0` is impossible for a dispatch
   that consumed 541,951 tokens. ⭐ **A schema slot is not a measurement.** ⇒ **These four columns are
   the ONLY per-dispatch view of the thing D2 exists to attribute** — if D2 shipped against them, it
   shipped against zeros. Carried on their side as `PLAN-TRUTH-055` D3.

⭐ **This is the third independent reason the per-phase ranking is unusable, and the three do not even
agree on direction**: loop-back spend unabsorbed (under-counts the earlier phase), whole-row omission
at close (under-counts the dropped phase), and the corpus blending two effort regimes (a weighted
average whose weighting is a sampling artifact). ⛔ **Do not attempt a correction factor across three
mechanisms with three directions.**

## Claim Labels

- **HYPOTHESIS (second-hand, `truthful-signals-027`)**: the billing formula reconstructs exactly as
  `input + output + 1.25·cache_creation + 0.1·cache_read`. Confirm/refute against a phase block in
  `work/metrics.toon` (verify-at-outline). **D1 is this verification.**
- **HYPOTHESIS (second-hand)**: `cache_read` = 76.1% of billing weight, `output` = 1.1%, exploration
  = 79.6% of tool-result bytes. Confirm/refute by re-parsing the archived corpus (verify-at-outline).
- **HYPOTHESIS, explicitly flagged as unestablished by its own author**: exploration bytes are the
  dominant *cause* of `cache_read`. Strongly suggested by the 79.6% share and the phase correlation,
  **not established** — ⭐ **D2 is precisely what would establish it, so this plan must not assume
  it.**
- **OBSERVED (first-party, this epic)**: `metrics.toon` records `cache_read` per phase and carries no
  per-turn attribution of it to causing bytes — read at the CIS-027 landing analysis, where finalize
  spend could be stated per phase but not per cause.
- ⛔ **Verify-first clause**: the exploration-instrumentation field **postdates ~07-29**, so it is
  present on only a subset of archived plans (reported as 26 of 47). **Derive that population; never
  state a share over the whole corpus that was computed over the instrumented subset.** If the two
  populations are conflated, D1 reproduces the exact partition-labelled-as-a-whole defect
  `PLAN-TRUTH-035` exists to fix.
- ⛔ **Verify-first clause**: `[STEP]`/marker-derived counts are a **FLOOR, not a count** (see
  PLAN-CIS-011 D6 — 9 of 16 steps carry `[STEP]` evidence). Settle the enumeration mechanism before
  any coverage figure in D1 or D4 is asserted.

## Expected Surface

- **HYPOTHESIS**: the `metrics.toon` writer and its phase accumulator (verify-at-outline)
- **HYPOTHESIS**: the tool-result byte categoriser that emits the exploration/execute/orchestration/
  work buckets (verify-at-outline)
- **HYPOTHESIS**: `plan-marshall:manage-metrics` or its equivalent owner — resolve via
  `architecture which-module` at outline rather than assuming (verify-at-outline)
- **OBSERVED**: `.plan/local/archived-plans/**/work/metrics.toon` — the read-only corpus D1 parses

## Dependencies and Sequencing

- ✅ **BAR LIFTED 2026-08-03 — PLAN-CIS-028 SHIPPED as #1080 (`e1ae38142`).** The clause below is
  retained as the record of why this plan was held at the queue head rather than emitted, and
  because its `record-metrics.md` / `plan-retrospective` adjacency is now a **merged-state** concern
  rather than an open-PR one: ⛔ **#1080 moved `plan-retrospective` to `order: 995` and left
  `record-metrics` at `order: 998`, so the retrospective still reads `metrics.md` before the
  accumulator closes.** That is an OPEN defect this plan's surface sits directly on top of — settle
  it at outline rather than measuring around it.
- ⛔ **(HISTORICAL, bar now lifted) CONCURRENT WITH PLAN-CIS-028 (PR #1080 open) — verified disjoint
  at FILE level, adjacent at
  CONCEPT level. Re-verify at outline before touching anything.** The write surface here is
  `manage-metrics/scripts/manage-metrics.py` plus the `platform-runtime` byte categoriser. CIS-028's
  branch touches `phase-6-finalize/standards/record-metrics.md` and `plan-retrospective/` — the doc
  that *calls* the writer and a *consumer* of its output, **not the writer itself**. ⛔ **Do NOT edit
  `record-metrics.md` or anything under `plan-retrospective/` while #1080 is open** — that is exactly
  the same-namespace-different-file shape that cost this epic 90 minutes on the ADR-012 collision.
  If the work genuinely needs either file, **stop and hand back to the orchestrator** rather than
  taking it.
- **Depends on**: nothing in this epic. ⭐ **This is the one wave-1 item that is unblocked and
  binary-verifiable today** — its success test is *"does the metric exist and reconcile to the phase
  total?"*, which needs no token measurement to be trustworthy first.
- **Gates**: the substrate's own value case (L4 — structured-answer substrate replaces match-dump
  exploration) and the sibling epics' L5/L6. ⛔ **None of them can be sized or verified until this
  lands.**
- **Adjacent to**: `PLAN-TRUTH-035` (`truthful-signals`) — the rendered `Total` is a partition
  labelled a whole. Different surface (renderer vs instrumentation), **so they may run concurrently**
  across the two epics; they are not the same plan and neither blocks the other.
- **Overlaps with**: PLAN-CIS-011 and PLAN-CIS-022 (`token-ledgers-disagree-and-the-smallest-is-named-actual`)
  — ⛔ **CIS-022 is the nearest neighbour and may touch the same ledger surface. Never pair; check
  disjointness explicitly before emitting either.**

## ⚠ Anti-goals inherited from the roadmap

- **Do not quantify a saving.** Every figure carried here is a *share of measured spend*, never a
  projected reduction. This plan exists **because** the savings are currently unsizeable.
- **Do not add the dispatched and inline populations into a new headline.** They are measured
  differently. ⭐ The originating finding's own "excludes 76%" headline performs exactly the
  arithmetic its next paragraph forbids — **do not inherit that error.**
- **Do not optimise step counts, candidate counts, or dispatch counts.** All are proxies for the 1%.
- ⛔⛔ **Do not propose lowering effort levels.** Measured first-party: it is the one intervention that
  improves the token number while degrading defect detection. See § "the raise paid for itself".

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-030-context-byte-attribution-instrumentation.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
