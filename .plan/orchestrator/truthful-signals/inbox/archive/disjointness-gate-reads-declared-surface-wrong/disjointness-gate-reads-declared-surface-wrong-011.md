envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:44:19Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# review_commitments reconcile returned `clear` over an empty commitment population

## What happened

Finding `418f3d`. `finalize-step-simplify`'s `review_commitments reconcile` returned:

```
verdict: clear
commitments_considered: 0
deletions_considered: 1
```

on a run where **13 self-review findings had been resolved `fixed` across six
commits** (`ec901ef48`, `37a7ddacd`, `5777c33c7`, `5c206c480`, `9d4266292`,
`530b1b80e`).

The seam anchored **none** of them. Its `clear` is therefore a
*nothing-was-comparable* clear, not a checked negative: it would have returned
`clear` whatever the simplify pass deleted — including a deletion that reversed a
narrowing commitment the review had made earlier in the same run.

No harm this run, because the pass applied 0 edits. The guard was vacuous, not
merely lucky.

## Why it matters

This is the fifth instance in one run of the archetype the plan itself exists to
close — an unresolvable population rendering as a clean pass instead of a distinct
third state — and it is the one instance sitting **in the finalize seam that guards
the plan's own run**. It is also a direct violation of this plan's own shipped rule:
`admits_disjointness_check: false` must never render as `disjoint`.

It belongs to the standing project archetype **"every set-guarding detector must be
population-derived"**: a check that can return `0` from an empty population MUST
publish the population size. Here the population size *was* published
(`commitments_considered: 0`) but was not made load-bearing — it rode alongside the
verdict instead of deciding it.

**Filed because it was omitted from an enumeration.** Sibling candidate message 008
enumerates the run's instances of this archetype as "three prior instances ... already
filed (rename-blind footprint derivation; window-dependent ledger reconciliation;
unarchived red CI run)". `418f3d` is a fourth, in a fifth component, and was not in
that list — the enumeration-does-not-discharge-a-class lesson from this same run,
recurring in the reporting of the class itself.

## Rule

A verdict computed over an empty population is not a negative result. When a
detector's comparable population is zero **while evidence exists that it should not
be**, return `indeterminate`, not `clear`. Publishing the population count is
necessary but not sufficient — the count must gate the verdict.

## Remedy shape

Make `commitments_considered` a first-class discriminator in
`review_commitments.py`: return `indeterminate` when it is zero while resolved
findings exist for the run, rather than `clear`. Separately, investigate why the seam
anchored none of 13 `fixed` findings — a reconciler that anchors 0 of 13 has an
anchoring defect underneath the reporting defect.

## Status

`pending` at landing; not fixed in-run.
