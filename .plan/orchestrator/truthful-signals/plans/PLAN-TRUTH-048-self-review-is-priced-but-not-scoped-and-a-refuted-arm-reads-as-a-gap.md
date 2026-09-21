> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-030`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-048: self-review is priced but not scoped — 709K tokens for the class it cannot reach

epic: truthful-signals
workstream: WS-01

⭐⭐ **TOKEN-REDUCTION LEVER — lever L8 in `roadmap-token-reduction.md`, and the first one carrying
measured first-party numbers rather than an estimate.** Token reduction is operator priority 1.

## Objective

`pre-submission-self-review` spent **709,472 tokens — 13% of `PLAN-TRUTH-010`'s entire ~5.5–6.2M
spend** — on **one finalize step**, and missed the run's most consequential defect, which a **free
external reviewer caught in one pass at zero cost**.

⛔ **This is not an argument against self-review.** The step earned its keep on defect count. It did not
earn it on the defect that mattered, and **its price is invisible at the point the lane is configured.**

## OBSERVED — measured, from the plan's own records

- `decision.log` `64b2a4`: `pre-submission-self-review phase=6-finalize outcome=executed —
  total_tokens=709472, tool_uses=169, duration_ms=2342530`.
- **39 minutes** of recorded agent time across **5 passes**, ~2h wall (13:59 → 15:52) plus a re-fire at
  19:00.
- **10 defects found. 2 of the 10 were introduced by a prior pass of itself.**
  ⇒ **Net external yield: 8 defects for 709K ≈ 89K tokens per externally-caused defect.**
- ⛔ **Pass 4 (the convergence check) was killed by a harness stream stall at 15:00:24Z and re-run** — so
  part of the spend bought **nothing**. (Standing hazard: the harness kills background jobs.)

### What five passes did not catch

Clause (d) of `error-handling.md` — **text this plan authored, in its own central deliverable** —
contains a GOOD example demonstrating the anti-pattern the clause forbids, and that example had
**already been used to justify retiring a lesson** (`PLAN-TRUTH-047`). Five passes over that file did not
flag it. **CodeRabbit flagged it in one pass, once the PR was open.** The same pass also missed clause
(f)'s comment misnaming its own mechanism.

⭐ **The honest read**: self-review's yield is concentrated in **structural/mechanical** classes — what
the `ext-self-review-plan-marshall` candidate detectors surface deterministically. The class it
demonstrably does not reach is **semantic self-contradiction inside prose the same run just authored** —
exactly the class an independent reader is good at and an author re-reading their own text is bad at,
**however many times they re-read it**. ⚠ **Five passes is not five perspectives.**

## ⭐ Second OBSERVED item, same step, opposite direction: a pass is a change and needs review

Pass 3 caught that **pass 2's sweep had missed a copy of the edited construct living OUTSIDE the source
tree** (a lessons-corpus record).

1. **A self-review pass is a change, and a change needs review.** Treating pass 1 as verification and
   stopping leaves the passes themselves unverified. **The review passes' own defect rate here was 20%
   of total findings.**
2. **A sweep's scope is set by where the construct LIVES, not by where the plan EDITED.** *"I swept the
   tree I was changing"* is not the claim *"I swept every copy"*. ⛔ `.plan/` stores, lessons corpora and
   generated targets are **inside** the population for any construct with a copy there.

⛔ **These two findings pull in opposite directions** — fewer passes is cheaper, more passes is safer.
**That tension is the plan's central design problem, and D2 must resolve it explicitly rather than pick
the half that suits the framing.**

## ⭐ Third OBSERVED item: a refuted arm reads as a missing deliverable

Three of this plan's request arms were **refuted on contact**, each cheaply — and each **cheaper still at
outline time**:

| Arm | Premise as written | Ground truth |
|---|---|---|
| D4 — leaf record-before-return invariant | missing, needs authoring | **already landed** in `agents.md` |
| D4b — fail-closed on unmappable paths, example `.claude/skills/**` | the named example is fail-open | the **example** was already fail-closed; the **class** was real at three OTHER shapes |
| launch-abort pin | launch abort is fail-open | already fail-closed (a negative returncode maps to `killed`) |

⭐ **The failure mode is not "the request was wrong."** It is that an arm's premise was carried into
implementation **as a given**, and the plan's one-deliverable-per-arm shape made a refuted arm look like
**a gap in delivery** rather than a **result**.

⛔⛔ **Note row 2 especially: a wrong example does not refute the class.** Dropping D4b because its
literal example was already fail-closed would have discarded a **live defect present at three other
shapes.**

## ⭐⭐ 2026-08-03 — THE DECISIVE EVIDENCE, from PLAN-TRUTH-035 / #1083 (`-004`, `-003`)

### Three consecutive passes each found "the last site" and each was wrong

`pre-submission-self-review` fired **five** times; three consecutive firings each found **exactly one
real defect**. ⛔ **That is not three independent finds — it is ONE doc cascade that each pass
mis-scoped, each time asserting a closure it had not verified.**

| Pass | Sites known | Sites actually live | Claim made |
|---|---|---|---|
| CodeRabbit `2ec3e0` | 2 → 3 | **4** | "three documentation sites overstate the trigger" |
| Self-review `3cb5d8` | 3 | **4** | "corrected exactly this trigger wording" — left `SKILL.md` stale |
| Self-review `820969` | 4 | 4 | the 4th site was **18 lines below prose the previous pass had just corrected IN THE SAME FILE** |

⭐⭐ **The fourth site is the damning one**: `data-format.md` :278-279 still named the old condition while
:257-260 of the **same document** had already been rewritten. **A pass edited that file and declared the
cascade closed without re-reading the rest of it** — and that section is the authority every sibling doc
cross-references.

⇒ ⭐⭐ **Only the final pass ENUMERATED the population (`git log -S` over the claim string) instead of
sampling. That pass found nothing further, and it is the ONLY "nothing further" in the sequence.**

⛔ **This is the strongest possible statement of D2's thesis**: *five passes is not five perspectives.*
Passes 1-4 cost real tokens to produce **three false closures**, and the fix was not "one more pass" —
it was **changing the method from sampling to enumeration**. ⇒ **D2's stopping rule must key on
"was the population enumerated?", NOT on "did a pass converge?"** — convergence is exactly what passes
1-4 each reported.

### And the bots caught what five passes did not — again

`-003`: the plan's fix **reintroduced its own target defect on a second run** (`cmd_enrich` keyed the
inline fold on `total_tokens` being falsy; run 2 reads the value run 1 wrote, falls through, and silently
drops the `(spans populations)` marker the plan existed to add). ⭐ **Caught by CodeRabbit AND pr-agent
independently, on the same lines, with the correct fix** — self-review did not.

⇒ **Second measured instance of D3's claim** (do not spend budget where an external reviewer is already
free), now with the class named: **idempotency of a fix against its own target defect.**

## Deliverables

1. **D0 — GATE: publish the price.** Surface the step's recorded token cost in its `display_detail`, so
   709K is visible **where the lane is configured**, not only in a retrospective. ⛔ Cheap, and it is the
   precondition for every other decision here being made on evidence.
2. **D1 — the step declares what it is NOT expected to catch.** *"5 passes, 10 defects found and fixed,
   converged"* **reads as a coverage claim; it is a volume claim.** ⭐ Recurrence of the standing
   **volume-read-as-coverage** archetype — cite it, do not re-derive it.
3. **D2 — calibrate the stopping rule on MARGINAL YIELD, not on convergence alone**, and resolve the
   tension above. Passes 1–3 each found defects; pass 4 converged; pass 5 (a loop-back re-fire) found 1.
   Candidate: scope passes beyond the first two to **newly changed text** rather than re-sweeping the
   whole footprint. ⛔ **Whatever is chosen must still satisfy "a pass is a change that needs review" —
   state how, or record that it does not and why that is acceptable.**
4. **D3 — do not spend budget where an external reviewer is already free.** The PR review runs
   regardless. Self-review's comparative advantage is **catching what blocks the PR from being worth
   opening**, not duplicating what CodeRabbit does better. ⚠ **Do NOT reduce this to "run fewer
   passes"** — the measured gap is a *class* gap, not a *count* gap, so the remedy is re-scoping, and a
   naive cut would lose the structural yield the step does deliver.
5. **D4 — a sweep states its POPULATION.** Which trees, which stores — checked against where the
   construct can actually live.
6. **D5 — outline verifies each arm's PREMISE before sizing its deliverable.** An arm whose premise is
   already satisfied is **closed at outline**, not carried into execution. ⛔ When a premise is refuted
   **at its literal example, re-test the CLASS at other shapes before closing it.** Refuted arms are
   reported in the landing as **results with their evidence**, never as silently-absent deliverables —
   that is what stops the epic re-queueing them as "unfinished".

⚠ Six deliverables, **at the bloat threshold**. Split evaluated: **D5 is the split point** (phase-3-outline,
a different surface from the finalize step). Kept together because D5 is the *upstream* half of the same
economics — a premise verified at outline is a deliverable self-review never has to review.
⛔ **If D0 shows the two surfaces have no shared consumer, SPLIT before implementation.** Rationale
recorded per the standing correction that the split decision belongs to staging.

## Claim Labels

- **OBSERVED (plan-reported, first-party, quoting `decision.log` `64b2a4` verbatim)**: 709,472 tokens,
  169 tool_uses, 2,342,530 ms, 5 passes, the 13:59→15:52 window, the 19:00 re-fire, 10 defects with 2
  self-inflicted, the 15:00:24Z harness kill, and the pass-3-caught-pass-2 sequence.
- **OBSERVED (this orchestrator, corroborating)**: CodeRabbit's clause-(d) finding is independently
  recorded in `PLAN-TRUTH-047` from the same run's decision log.
- ⚠ **The 13% figure depends on which total you use** — 709K against the published 2.78M is **25%**,
  against the reconstructed ≈5.47M is **13%**, against `record-metrics`' 6.2M is **11%**. ⛔ **This plan
  must NOT quote a single percentage until `PLAN-TRUTH-035` settles which total is the whole.** The
  absolute 709,472 is solid; every ratio built on it is not. ⭐ **This is the epic's own thesis biting
  the plan that would fix it.**
- **HYPOTHESIS**: the missed class is *semantic self-contradiction in freshly-authored prose*. ⚠ Drawn
  from **n=2 defects in one run** (clauses (d) and (f)). Plausible and consistent, **but two data points
  are not a class.** ⛔ **D1 must not encode this as the declared non-coverage until it is checked against
  more runs** — encoding a wrong non-coverage claim would *create* a blind spot rather than document one.

## Expected Surface

- **HYPOTHESIS**: `pm-plugin-development:ext-self-review-plan-marshall` — passes, stopping rule, detectors
- **HYPOTHESIS**: `phase-6-finalize` — the step's `display_detail` and lane configuration
- **HYPOTHESIS**: `phase-3-outline` — D5's premise verification

## ⭐⭐ 2026-08-03 — a SECOND independent first-party measurement, and it dissolves the circularity

`code-intelligence-substrate` measured the **same step** on **#1080**:

| | This plan (#1082) | `PLAN-CIS-031` (#1080) |
|---|---|---|
| Cost | **709,472** tokens | **2,979,307** tokens across **13 dispatches** |
| Share | 13% of the plan (see caveat) | **56% of 6-finalize, 30% of the whole plan** |
| Waste signal | 2 of 10 findings **self-inflicted** | **4 of 13 rounds found nothing**; **8 of 19 findings were rework** |

⇒ ⭐ **Two independent first-party measurements, an order of magnitude apart in absolute terms,
agreeing on the shape.** **That convergence is worth more than either number** — and it is the first
time this epic has had a lever corroborated across epics before implementation.

### ⛔ The circularity is DISSOLVED, not confirmed — correcting my own framing

I recorded that L8 is *"blocked behind the measurement it would fund"*. **Their answer is correct and I
am adopting it:** the share being 25% / 13% / 11% blocks **the claim about how much it saved**, not
**permission to do it**.

⭐ **CIS-031's success test is structural and binary**: *does round N+1 sweep only the paths changed
since round N's `head_at_completion` — yes or no?* ⇒ **Neither lever waits on L3.**

⛔ **This is the same discrimination I accepted FROM them on L4a/L4b and then failed to apply to my own
lever.** Recorded as the recurrence it is: *split levers by whether success is verifiable WITHOUT the
measurement being fixed* — I wrote that rule into the roadmap and then did not run it on L8.

### ⛔ A trap they hit that this plan will hit too

Delta-scoping keys on **`head_at_completion`, which is not reliably written** — #1080 paid a **full
re-dispatch of `lessons-housekeeping`** for a `done` record that omitted it.

⇒ **Settle that the field is present before depending on it**, or a delta-scoped round **silently
degrades to a full sweep and this plan ships a no-op** — the vacuous-guard archetype, at n≥5, arriving
inside the fix for a cost problem. **Add this as a D2 precondition.**

## Dependencies and Sequencing

- ✅ **NOT blocked on `PLAN-TRUTH-035`** — corrected above. Only the *savings claim* is; the structural
  re-scoping proceeds now.
- ⚠ **Coordinate with `PLAN-CIS-031`** — same step, same lever, two epics. ⛔ **Read their spec at D0**;
  if they are implementing the delta-scoping, this plan's D2/D3 must not re-implement it and should
  narrow to the *declaration* half (D1's non-coverage statement, D0's published price).
- ⚠ Related to `PLAN-81` (self-review cannot see an unreachable guard, **SHIPPED #1042**) — same step,
  a *capability* gap where this is an *economics and scope* gap. **Read PLAN-81's landing before
  outline; do not re-derive its findings.**
- ⚠ Adjacent to `PLAN-TRUTH-047` (the defect self-review missed) — **047 owns the defect, this owns the
  economics.** Do not merge.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-048-self-review-is-priced-but-not-scoped-and-a-refuted-arm-reads-as-a-gap.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
