envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=candidate-lesson
created=2026-09-06T19:32:16Z

# Guards written to close a completeness gap reproduced the gap they were closing

component: plan-marshall:phase-6-finalize
category: anti-pattern
confidence: medium
source_plan: exit-code-convention-stops-at-the-skill-boundary
source_pr: 1423, 1429

## Context

This plan's D4 existed to *guard* a derived population — to make the exit-code
convention's coverage checkable rather than asserted. Four defects were found
inside the guards it wrote:

1. a vacuous `assert X == X`
2. a false universal claiming every executor-invoking document references the standard
3. an order-dependent classifier
4. a reachability-first test that would accept a forbidden heading

Two were caught by local passes, two by CodeRabbit on review.

The fourth is the notable one. Lesson `2026-08-27-16-005` — the lesson this plan
was effectively implementing — already described exactly that failure, in its own
Root cause section:

> the contract test pinned a *heading string* because that is the only thing all
> ten copies reliably share, which is precisely why it could not detect the body
> being gutted.

The lesson's finding `653ace` is the same defect. It recurred inside the fix for
the lesson that described it.

## Root cause

A guard authored in the same pass as the change it guards is written from the
author's model of the change, not from an independent derivation of the property.
That makes the guard's population and the change's population the *same* claim, so
the guard cannot fail for the reason the change is wrong — it can only fail if the
author's model is internally inconsistent.

All four defects share that shape: `assert X == X` compares a value to itself; the
false universal asserts closure over a set the author believed complete; the
order-dependent classifier encodes the order the author happened to write; the
heading-pin protects the token the author used as the marker rather than the body
that carries the meaning.

This is the project's existing vacuous-guard archetype, and the notable recurrence
condition is that it appeared *in a plan whose explicit purpose was to make a
contract checkable* — the intent to guard is not protective against it.

## Proposed action

1. When a task authors a guard over a population the same plan derived, require
   the guard's population to be re-derived independently of the change's, and
   require the guard to publish its population size on a passing run (this plan's
   D4 did adopt the publish-the-size rule — keep it, and extend it to the
   re-derivation).
2. Add the four shapes above to the pre-submission self-review candidate set as an
   explicit guard-quality pass, run against *newly authored assertions*
   specifically. `pre-submission-self-review` did fire on this plan and found the
   over-claimed universal (1 defect class, 3 sites) — so the pass works; it needs
   the remaining three shapes in its candidate list.
3. Where a lesson being implemented names a guard defect in its own Root cause,
   treat that named defect as a required check on the implementing plan's guards.

## Evidence

- `manage-lessons get --lesson-id 2026-08-27-16-005` — Root cause paragraph quoted above; finding `653ace`
- `status.metadata.phase_steps` `pre-submission-self-review` —
  `"1 defect class, 3 sites: over-claimed universal narrowed to the derived population"`
- `project:finalize-step-review-retrospective` — 7 CodeRabbit findings reconstructed from PR surfaces
- `TASK-006` — "Retarget the derivation and guard at the xref payload, and pin the
  single-body property", the rework that followed
