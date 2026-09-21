envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:34:23Z

component=plan-marshall:manage-execution-manifest
category=improvement

⛔ **FOLD REQUEST — recurrence of `-016`** (a gate with no declared `verdict_inputs` re-fires on every HEAD advance). This report widens it: **three** finalize steps re-fire, not one. Please fold onto the same item.

Relayed from Token-Sheriff PLAN-08 (PR #730 / `c40963ac`).

# Candidate lesson: three finalize steps re-fire on every HEAD advance because none declares a `verdict_inputs` surface

**Origin signal**: run observation offered by the orchestrator for judgement (not one of the three counted signals).
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).

## Observation

`phase-6-finalize`'s verdict-currency classifier returned **`invalidated`** with reason
**`verdict_inputs_undeclared`** for three steps:

- `pre-push-quality-gate`
- `pre-submission-self-review`
- `finalize-step-simplify`

None of the three declares a `verdict_inputs` surface. The classifier's fallback for an
undeclared surface is to treat the prior verdict as invalidated, so **every HEAD advance
re-fires all three**.

## Why it is candidate-lesson shaped

The fallback is individually correct — a step that does not say what its verdict depends
on cannot be shown to still hold, and assuming currency there would be the fail-open. But
the aggregate effect is that the currency mechanism does no work for these three steps:
they are unconditionally re-run, so the classifier is pure overhead on this path, and the
finalize loop pays their full cost on every loop-back round.

Three steps sharing the same undeclared-surface reason is the signal. This is not one
step that forgot a declaration; it is the declaration being absent across the steps that
would benefit from it most (a quality gate, a self-review, and a simplification pass are
exactly the expensive, re-firing ones).

Possible correctives (for the orchestrator to judge):
1. Declare `verdict_inputs` on these three steps so the classifier can actually discharge
   a still-current verdict instead of invalidating by default.
2. Or, if the honest answer is that these steps genuinely depend on the whole tree, say
   that explicitly — a declared "depends on HEAD" is different from an undeclared
   surface, and only the first tells a reader the re-fire is intended rather than
   accidental.

## Cross-plan judgement deferred

This one is plainly cross-plan: it is a property of the finalize step definitions, not of
this plan's change. Whether it becomes an epic-scoped work item, a global lesson, or an
owed follow-up against `phase-6-finalize` is the orchestrator's call. This plan transmits
the candidate only.
