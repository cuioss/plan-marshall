# PLAN-CIS-037: The Dispatch-Boundary Ledger Is Not a Commensurable Population

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-08 by SPLITTING `PLAN-CIS-011`, which had accreted to **eleven deliverables** — the
> worst split-guard breach in the queue. This spec takes the **boundary-ledger arithmetic** arm
> (CIS-011's former D8, D10, D11); CIS-011 keeps the **step/dispatch emission** arm; `PLAN-CIS-038`
> takes the **manifest frozen-vs-live** arm.
>
> ⭐ **The three items moved here are not merely adjacent — they explicitly compound with one another
> in CIS-011's own text**, and each was filed as a candidate explanation for the others. Keeping them
> together is what makes them tractable; keeping them beside eight unrelated deliverables is what made
> CIS-011 unshippable.

## Objective

The dispatch-boundary ledger is the **only per-dispatch view of context spend** — it is what
`PLAN-CIS-030`'s attribution work reports against and what `PLAN-CIS-035` divides by. It currently
publishes a coverage ratio whose numerator and denominator come from **different populations**, omits
**whole dispatch classes** without saying so, and **mislabels exact agreement as a discrepancy**. Make
the ledger a declared population whose figures are commensurable, or make it say what it excludes.

## Why this is ours

Evidence emission about our own runs, and the substrate every token-reduction claim this epic makes is
divided by. Routing test 2 — no PR/review surface.

## The three defects are one defect seen from three angles

⭐ **This framing is the reason for the split and should survive into the outline.** Each item was filed
separately, and each turns out to be a symptom of *the ledger having no declared population*:

| Angle | Symptom | What it says about the population |
|-------|---------|-----------------------------------|
| **The ratio** (D2) | `17 of 9 dispatch(es) recorded — complete` | numerator and denominator are drawn from different sets and nothing asserts commensurability |
| **The omission** (D3) | `2-refine` and `q-gate-validation` spawns record **no** boundary at all | the denominator's set structurally excludes some dispatches |
| **The comparator** (D4) | equal totals annotated *"smaller than total_tokens"* | the comparison asserts a strict inequality that does not hold |

⇒ ⛔ **D3 is very likely the mechanism behind D2.** If whole classes never register, a numerator counted
one way and a denominator counted another **cannot** agree, and `17 of 9` becomes an *expected outcome*
rather than an anomaly. **D2 must test D3 as its first candidate explanation before treating the ratio
as an independent defect** — fixing the ratio while the class omission stands would produce a clean
figure over an incomplete set, which is strictly worse than a visibly impossible one.

## Deliverables

### D1 — GATE: declare the population (mutates nothing)

Answer, before changing anything: **which set of dispatches is the ledger's denominator meant to be?**
Enumerate the dispatch classes that exist, then determine for each whether it registers a boundary.
⛔ **Derive the class list from the dispatching code, never from a list of classes observed in a run** —
a run-derived list cannot contain a class that never registers, which is precisely the defect. Report
the class count and the registering count as two separate figures.

### D2 — a recorded-vs-expected ratio is commensurable or it does not render

**OBSERVED first-party** (`PLAN-CIS-001` / PR #1084): the `6-finalize` row rendered
`17 of 9 dispatch(es) recorded — complete`.

⛔ **`17 of 9` is not a ratio, and the verdict attached to it is `complete`** — the surface that exists
to report coverage emitted an arithmetically impossible figure and **certified it**.

Numerator and denominator must be derived from **one declared population**, and a ratio whose numerator
exceeds its denominator must be a **loud failure**, never `complete`. ⛔ **Do not fix by clamping the
display** — a clamped `9 of 9` is the same defect with the evidence removed.

### D3 — every dispatch records a boundary, or the ledger names the classes it excludes

**`2-refine` and the `q-gate-validation` spawns record no dispatch boundary whatsoever.**

✅ **Confirmed on an INDEPENDENT plan**, which is what lifts this from an artifact of our runs to a
general defect: an operator-supplied `metrics.md` for `plan-45-demo-client-doc-consolidation` — **a plan
neither this epic nor `truthful-signals` ran** — carries **no `Dispatch-boundary total` for `2-refine`
or `3-outline` at all**, while `4-plan` / `5-execute` / `6-finalize` each have one. Same two phases,
different plan, different epic.

⇒ **The EXISTENCE of the defect is established; the SWEEP is still owed to establish its SIZE.**
⛔ **Silent exclusion is the defect** — a ledger that omits a class without saying so is
indistinguishable from a class that did not run.

### D4 — the comparator stops mislabelling exact agreement

`6-finalize` reported `Dispatch-boundary total: 2,468,507` beside `Total tokens: 2,468,507` —
**identical** — annotated *"recorded; not preferred — smaller than total_tokens under same-population
max"*. ⛔ **Equal is not smaller.** The max-selection is arithmetically fine; the **message** asserts a
strict inequality that does not hold, so a reader is told the ledger under-counted when it agreed
exactly.

⭐ **This is worth more than a wording fix, and the deliverable should say why**: an exact agreement
between two independent producers is **the single most valuable signal this surface can emit** — it is
the reconciliation identity `PLAN-CIS-030` D2 proved by arithmetic — **and it is currently rendered as a
discrepancy.** A reader trained by this message learns to distrust the one case that should build trust.

### D5 — tests, each verified to FAIL pre-fix

(a) A ratio whose numerator exceeds its denominator renders as a failure, never `complete`.
(b) A dispatch class that registers no boundary is named in the ledger's exclusion list.
(c) Equal boundary and total figures are annotated as agreement, not as a shortfall.
⚠ Per the epic's standing rule, each test is verified to fail against current code **before** the fix;
a test that passes today is a characterization test and must be labelled as one.

Five deliverables — under the split guard.

## Claim Labels

- **OBSERVED (first-party, PR #1084)**: the `17 of 9 … complete` render.
- **OBSERVED (first-party, operator-supplied `metrics.md`, plan-45)**: the equal-totals mislabel, and
  the absent `2-refine` / `3-outline` boundary totals on a plan neither epic ran.
- **HYPOTHESIS (verify-at-outline)**: that D3 is the mechanism behind D2's ratio. Confirm/refute by
  determining whether the numerator's and denominator's populations differ **by exactly the
  non-registering classes**. ⛔ This is a real fork: if they differ by something else, D2 has a second
  cause and fixing D3 will not close it.
- **HYPOTHESIS (verify-at-outline)**: that `2-refine` and `q-gate-validation` are the complete set of
  non-registering classes. ⛔ **Almost certainly a FLOOR, not the set** — it is a two-run sample, and
  the epic's standing rule is that a named list is a sample. D1 derives the real set.

## Expected Surface

- **HYPOTHESIS**: `manage-metrics` — the dispatch-boundary record writer and the recorded-vs-expected
  renderer (verify-at-outline; the orchestrator did not locate the render site first-party).
- **HYPOTHESIS**: the dispatch sites that fail to register — `phase-2-refine` and the q-gate validation
  spawn path (verify-at-outline).
- **OBSERVED**: `plan-retrospective`'s consumption of the boundary figures — read-only here; the render
  path belongs to `PLAN-CIS-020`.
- **OBSERVED**: tests under `test/plan-marshall/manage-metrics/**`.

**Disjointness:** ⛔ **WS-04 serialization class — never pair with `PLAN-CIS-011`, `PLAN-CIS-034`,
`PLAN-CIS-035`, `PLAN-CIS-030`'s residue, or `PLAN-CIS-020`.** This plan and CIS-011 were one plan until
2026-08-08 and still share the `phase-6-finalize` dispatch neighbourhood; the split is a scoping fix,
**not** a disjointness claim.

## Dependencies and Sequencing

- ⛔⛔ **THIS PLAN — NOT ALL OF `PLAN-CIS-011` — IS `PLAN-CIS-035`'s BLOCKER, and that is the single
  most useful consequence of the split.** CIS-035's D1 computes shares of dispatch spend against this
  denominator, and the epic's standing note *"CIS-011 must land first; D1's shares need a denominator
  that is not `17 of 9`"* was written when D8 lived in CIS-011. **It does not any more.** ⇒ **CIS-035
  is blocked on CIS-037 only**, and CIS-011's emission arm may now land in any order relative to it.
- **Relationship to `PLAN-CIS-011` D9** (an operator resume emits no step instrumentation): D9 stays in
  CIS-011, but it hands this plan a **candidate explanation to rule in or out** — a resumed run may
  contribute to numerator and denominator inconsistently. D2 must consider it alongside D3.
- **Relationship to `PLAN-CIS-030` (#1086, shipped)**: that plan established the attribution identity on
  one phase. This plan is why the other five phases cannot yet be checked the same way.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-037-dispatch-boundary-ledger-is-not-a-commensurable-population.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
