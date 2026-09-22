# PLAN-TRUTH-173: The in-run self-review instrument — detector reach, a bounded terminus, and six ways a guard goes vacuous

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-18 from **two hand-offs from `review-apparatus`**, which routed them out under the standing
PR test — neither is about the automated PR-review pipeline, both are about the **in-run self-review
instrument**:

- `review-apparatus-042.md` — two corpus lessons (`2026-09-15-06-002`, `2026-09-13-20-003`). ⛔ Both were
  retired from the corpus by this epic's 2026-09-18 sweep, so read them at
  `.plan/local/orchestrator/truthful-signals/lessons/{id}.md`, never from `manage-lessons`.
- `review-apparatus-043.md` § Set 1 — four deliverables from its retired `PLAN-PR-062`, whose bodies stay
  readable at `.plan/local/orchestrator/review-apparatus/plans/` (`PLAN-PR-049` / `PLAN-PR-030`).

⭐ **The sender asked for these to be staged together or not at all**, because the lessons and the
deliverables are one subject. They are staged together here.

## Objective

**The instrument that reviews a plan's own diff before submission cannot say what it examined, cannot stop,
and its guards keep going vacuous in ways it does not detect.** Three failures, measured rather than
asserted:

- **Reach** — 4 of 5 observed escapes are *not* the class the detector looks for. They are a closed-set
  literal sitting beside the named symbol that defines the same set, and **none of the surfacer's 20
  `_detect_*` functions is that class**.
- **Termination** — **14 of 51 findings (27%) across 19 firings were self-seeded**, in five chains; one ran
  four consecutive rounds, and one OSCILLATED — deleted in one round, restored the next.
- **Vacuity** — six separately-diagnosed ways a guard goes vacuous, including **the fix for one
  self-defeating a round later** (widening an affirmative allowlist to bare `write` auto-satisfied the
  condition, because `write` is itself a forbidden target).

⭐ The terminating move is already known and is the cheapest part: **replace a drifted restatement with a
POINTER at its source, never with a corrected restatement.**

## Deliverables

Six deliverables. D0 is a gate.

**D0 — GATE: derive the detector-class population and the self-seeding rate.** Enumerate the surfacer's
`_detect_*` functions against the escape classes actually observed, and re-derive the self-seeded share
over the firings available at HEAD. ⛔ Publish both with their populations — the 27% and the 4-of-5 are
carried measurements from another epic's run and must be re-derived here before they are acted on.

**D1 — The closed-set-literal detector the instrument lacks.** A hard-coded literal beside the named symbol
that defines the same set is the dominant escape class and no detector covers it. Population-derived, and
it publishes the population it evaluated. *(`PLAN-PR-062` D5 + its amendment.)*

**D2 — A bounded terminus for the review chain.** The loop stops on a computed signal rather than on
exhaustion. The published stop signal is the self-seeded share per round; the default remediation posture
from round 2 onward is deletion-or-pointer. *(`PLAN-PR-062` D8 + its amendment.)* ⚠ Coordinate with
`PLAN-TRUTH-147`'s convergence folds and `PLAN-TRUTH-167` D2 (the round-invariant refusal): those own
*when the loop may stop*; this owns *what the stop signal is measured from*.

**D3 — A finished-edit detector for partial de-duplication**, population-derived, publishing the row or
list size it evaluated. *(`PLAN-PR-062` D9.)*

**D4 — The six vacuity modes, each with a matched control.** Positional indexing over named members; an
affirmative-verb allowlist incomplete by construction; **the fix for that one self-defeating a round
later**; an unanchored pattern satisfied by unrelated prose; a matched control transcribing a SUBSET of the
live constant; and a non-vacuity guard firing only on TOTAL emptiness, never on a shrunk population.
Instances closed in #1494 — **the authoring discipline is what carries**. *(Lesson `2026-09-15-06-002`.)*

**D5 — A self-application pass when the plan's subject IS a defect archetype.** Run the plan's own predicate
against the plan's own new code and report *N of M changed code paths examined*. ⛔ The datum that makes
this non-optional: `plan-truth-127` shipped its own thesis **inverted, twice** (`af0a4d`, `9e4ff2`), on a
tree green under `pre-push-quality-gate`, plugin-doctor, CI **and** a `109 candidates examined, no check
matched` self-review. *(Lesson `2026-09-13-20-003`; its action 3 is already shipped at
`pre-submission-self-review.md:286`/`:296` — D0 confirms what remains.)*

## Claim Labels

- OBSERVED (`review-apparatus-043`): 4 of 5 observed escapes are a closed-set literal beside its defining
  symbol (`a1ebb0`, `986369`, `bc1344`, `df7702`), and none of the 20 `_detect_*` functions covers it.
  ⚠ Measured by the sending epic, not here — D0 re-derives.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: truthful-signals/cleanup | rescoped: n/a | evidence: PR #1559 added ONE new detector, _detect_hoisted_binding_shadows (21 module-level _detect_* functions now, up from 20). It covers a hoisted-binding-shadow class, NOT the closed-set-literal-beside-its-defining-symbol class this claim names -- conclusion still holds, cited count updated from 20 to 21.
- OBSERVED (`review-apparatus-043`): 14 of 51 findings (27%) across 19 firings were self-seeded, five
  chains, one four rounds long, one oscillating. ⚠ Same caveat: re-derive at D0.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The 14-of-51 / 27% self-seeded share over 19 firings is a measurement taken in another epic's run; the source firings are still not on disk in this checkout. The spec's own caveat (re-derive at D0) stands, unaffected by PR #1559.
- OBSERVED (lesson `2026-09-15-06-002`): six separately-diagnosed vacuity modes, each caught by CodeRabbit
  or Q-Gate during `plan-truth-157`'s own review rounds; instances closed in #1494.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-15-06-002 present in the epic's lessons store; the six vacuity modes were still not individually re-read against _self_review_patterns.py (PR #1559 added 26 lines there) / the #1494 fixes this pass.
- OBSERVED (lesson `2026-09-13-20-003`): `plan-truth-127` shipped its own thesis inverted twice, and its
  action 3 is already shipped in `pre-submission-self-review.md`.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-13-20-003 present; neither the plan-truth-127 double-inversion nor the action-3-already-shipped half was re-read at HEAD.
- ⚠ HYPOTHESIS: the closed-set-literal class and the six vacuity modes are one detector family rather than
  two — ⛔ unsettled; D0 decides, and if they are one, D1 and D4 collapse (verify-at-outline).
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: One-detector-family-or-two question the claim assigns to D0.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — the 20 `_detect_*` functions (D0, D1, D3, D4)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — the pattern constants D4's modes live in
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — the loop and its stop signal (D2, D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — the surfacer contract D1/D3 publish through (verify-at-outline)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/` — D4's matched controls

## Dependencies and Sequencing

- ⛔⛔ **`review-apparatus` `PLAN-PR-074` D6 edits `_self_review_detectors.py` and `_self_review_patterns.py`
  and sweeps them for the six vacuity modes BEFORE editing.** That is scope discipline for their plan, not
  ownership — but it is the same two files this spec's D1/D3/D4 rewrite. **Cross-epic: no gate can see it.**
  Tell `review-apparatus` before launching, and sequence rather than pair.
- ⛔ Never pair with `PLAN-TRUTH-167` (shares `pre-submission-self-review.md`) or `PLAN-TRUTH-147`.
- ⚠ `PLAN-TRUTH-153` D9 owns population-derived set-guarding detectors generally; this spec owns the
  self-review instrument specifically. If D0 finds one mechanism, say so rather than building it twice.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-173-the-in-run-self-review-instrument-detector-reach-a-bounded-terminus-and-six-vacuity-modes.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
