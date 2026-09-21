envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:23Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high

# Re-check the neighbours of a corrected guard for the same archetype

## Context

This plan shipped through two pull requests. Of the six findings CodeRabbit raised on the second (#1434), four were defects in the plan's own repairs of the first PR's findings, not in the original change:

- `1f08b2` — a four-state fold (absent / unparseable / non-object / empty-object all reported as `file_not_found`) in the guard one level ABOVE the `b339df` fix. The same conflation `b339df` had just removed, re-introduced one level up.
- `d03b62` — a mirrored-constant coupling in the concurrency test that was rewritten for `b6c061`.
- `d5eea4` — a second documentation mirror left unchecked by the anchored test added for `54179b`.
- `e60d21` — an escalation on the `d5eea4` remedy itself.

`1f08b2` is the sharp case: the fix for a state-fold defect reproduced that exact archetype in an adjacent guard. Read the other way, the second review round earned its cost - a single round would have shipped both `1f08b2` and `d03b62` to main - but it earned it by re-reviewing repairs.

## Root cause

A fix is scoped to the line the finding names. Nothing prompts a check of the immediate neighbours - the caller and callee of a corrected guard, the sibling mirror of a corrected enumeration - for the same archetype the finding just identified. The archetype is known at fix time and is not applied outward.

## Proposed action

After a fix lands for an archetype-bearing finding, re-check its structural neighbours for the same archetype before submitting: the guards one level above and below a corrected state-fold, the sibling mirrors of a corrected enumeration, the matched control of a corrected test arm. This is a bounded, mechanical sweep with a named archetype, not an open-ended re-review.

## Evidence

- review-retrospective.md § "The unflattering measurement: a high second-order rate" — "Four of the six findings CodeRabbit raised on #1434 were about this plan's own remedies for its #1424 findings".
- review-retrospective.md Comparative Verdict — "1f08b2 re-introduced one level up the exact state-fold that b339df's fix removed one level down. A fix pass that re-checks the neighbours of a corrected guard for the same archetype would have caught it before review did."
- Task record: TASK-6/7/8 were the #1424 repairs; TASK-9/10/11 were the repairs of those repairs.
