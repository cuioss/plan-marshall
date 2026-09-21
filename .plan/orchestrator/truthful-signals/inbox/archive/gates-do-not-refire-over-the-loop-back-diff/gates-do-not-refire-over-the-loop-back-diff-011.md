envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:11:00Z

component=plan-marshall:phase-6-finalize
category=bug

# Vacuous mutation guard in test_head_dependence_derivation.py (recorded by finalize-step-simplify, not actioned)

## Observation

`finalize-step-simplify` recorded — and did **not** action — a **vacuous mutation guard** in `test_head_dependence_derivation.py`, a test file **shipped by PLAN-TRUTH-001 itself** in PR #1073.

A vacuous guard is a predicate that cannot fire: the assertion passes for reasons unrelated to the property it claims to check, so it contributes zero discriminating power while presenting as coverage.

## Why this is worse than an ordinary vacuous guard

Three aggravating factors stack here:

1. **It is in the test that guards the plan's central derivation.** The head-dependence derivation is PLAN-TRUTH-001's core deliverable. A vacuous guard there means the *one* thing most worth pinning is pinned by an assertion that cannot fail.
2. **It shipped.** It is live in merged main, not caught pre-merge.
3. **Archetype recurrence.** The vacuous-guard archetype now stands at **4+ recorded sightings, one of them introduced by a fix for it**. This one was introduced by a plan whose whole subject is "gates that do not actually re-check".

That last point is the epic-relevant one: a plan about non-firing gates shipped a non-firing gate. The archetype is scale-invariant — it appears at the workflow level (a gate that does not re-fire over the loop-back diff) and at the assertion level (a guard that cannot fire at all), and the same author reproduced it at both levels in one change.

## Why this belongs to `truthful-signals`

A vacuous guard is the purest form of the epic's theme: a **green that carries no information**, indistinguishable from a green that carries a lot. The test suite's pass count goes up; the actual coverage does not move.

## Suggested shape of the fix

1. Repair the specific guard so the mutation it claims to detect actually fails the test — verify by *making the mutation* and watching it go red.
2. The durable half: **every set-guarding detector must be population-derived**, and every guard must be validated by a deliberate mutation. A guard that has never been observed to fail is not a guard.

## Not actioned

Recorded by `finalize-step-simplify` during PLAN-TRUTH-001's finalize; deliberately not actioned in-run. Handed to the epic.
