envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:07Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# RECURRENCE (7th sighting): a fix for the hand-maintained-membership archetype reintroduced the archetype

## Observation

PLAN-TRUTH-001 exists to replace hand-maintained membership lists with registry derivations. During its own self-review iteration 2, **the plan's own fix reintroduced a hand-maintained membership fragment** — of exactly the archetype the plan removes. It was caught by iteration 3 (`finalize-step-simplify`), not by the author.

This is the **7th recorded sighting** of the archetype, and at least the second time the archetype has been introduced *by a fix for it*. The corpus already carries the sibling pattern "a vacuous guard introduced BY A FIX for vacuous guards".

## Why this keeps happening

When you are removing a hand-maintained list, the removal itself needs to know the membership — so the fix reaches for the membership *at authoring time*, which is exactly how the original list was born. The fix and the defect have the same shape; only the intent differs, and intent is not visible in the diff.

The pattern generalizes: **a fix authored against an archetype is written by someone holding that archetype's data in their head**, which is the precise cognitive state that produces the archetype. Removing a defect class from a codebase does not remove it from the author.

## Rule

When the change under authoring is itself a fix for a defect archetype:

1. **Re-run the archetype's own detector against the fix's diff** before submitting. If the archetype has a population-derived detector, point it at the new code. If it has none, that absence is itself the finding.
2. **The fix must not contain a literal instance of the thing it removes** — not in code, not in a test fixture, not in the doc prose that describes the fix. A "for example, the nine members are …" sentence added by the fix is a new hand-maintained list.
3. Treat a self-review pass that ends clean on iteration 1 of an archetype-fix as **suspicious**, not as done.

## Recurrence

7th sighting. Prior sightings span vacuous guards, doc-contract divergence, and enabled-bots-vs-operative drift. The generalization worth promoting: **fixes for a defect class are the highest-density source of new instances of that class.**
