envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:20:11Z

component=plan-marshall:automatic-review
category=bug

# review_completeness credits a thread acknowledgement as a fresh review, producing a false green on the merge gate

Carry-forward from plan `the-foreign-gate-population-and-branch-f-recovery` (finding
`852b0f`, resolution `accepted`). **Still live on main** — deliberately not fixed in
PR #1473.

## Mechanism

Observed on PR #1473 at head `3aee443ae` (iteration 8). `review_completeness check`
returned `participation_complete: true` with `coderabbit,participated`. The credit came
through the fresh-edit currency arm, satisfied by an INLINE comment that was CodeRabbit's
`22:46:45Z` resolution ACKNOWLEDGEMENT on a *previous* round's thread — not a review of
this head.

At that same moment CodeRabbit's own persistent walkthrough carried an explicit quota
REFUSAL for exactly this delta ("Reviewing files that changed between `4f283956d` and
`3aee443ae`", "Review limit reached"), and its coverage marker read
`final_review_risk_coverage sourceCommitId=coveredCommitId=4f283956d` — one commit behind.

The rule "a bot with any genuine review keeps its credit" (a bot in BOTH
`participated_bots[]` and `refused_bots[]` resolves to participated) is what let an explicit
refusal be outvoted by an edit that was not a review.

## Why it matters

This is a FALSE GREEN on a MERGE-GATING predicate. The dispatch that hit it refused to act
on it, but a less careful consumer would have marked the step done and cleared the barrier
over a head no required bot had reviewed.

## Remedy direction

The currency arm should require the edited comment to carry review-shaped evidence — a
coverage marker naming the awaited SHA, or actionable content — rather than treating any
fresh edit as participation.

## Pairing

Fix together with the sibling candidate for finding `658eec` (`pr wait-for-comments` samples
the newest comment, so an in-place refusal edit is invisible). They are two faces of one
wrong assumption about how these bots publish: a detector that reads only the newest comment
and a predicate that credits any fresh edit.

## Why it was not fixed in-run

The operator directed ONE round of automatic-review pipeline fixes at the merge gate
(`be9a8bcb8` + `4f283956d`). This was observed afterwards; fixing it would have advanced
HEAD and restarted the mandatory-review cycle, which had already cost three ~90-minute
quota waits on this PR. Containment was real rather than assumed: the false green was caught
and refused, and both required bots were independently proven at the merge HEAD by
body-level evidence.

File: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
