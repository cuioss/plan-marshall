envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:20:05Z

component=plan-marshall:automatic-review
category=improvement

# A required review bot gated the merge for a whole run while producing no actionable finding

On PR #1473, `cuioss-review-bot` is a REQUIRED bot: its participation gates the merge
barrier. Across the entire run it published nothing but contentless status summaries.

## What was observed

- All 12 `pr-comment` findings stored for this plan carry `author: coderabbitai`. Zero came
  from `cuioss-review-bot` — it contributed no claim about the code at any point in the run.
- Its only observed publish shape is an in-place edit of its persistent "Reviewer Guide"
  issue comment, whose body reads `(Review updated until commit <commit-url>)`. That is a
  currency stamp, not feedback.
- Its declared contract matches: `participation_evidence: issue_comment`, empty
  `completion_check_name` (see `automatic-review/standards/cuioss-review-bot.md`).
- Finding `ace227` (fixed in-run, `be9a8bcb8`) showed the consequence of that shape on the
  detector side: `head_sha_verified` was hard-coded `false` on the issue-comment path, so
  this bot could *never* return a verified re-review and every correct re-review it
  performed was classified `declined` — a blocking member whose documented remedy is
  demotion to `optional_bots` or a merge-authorization waiver.

So the run carried a required member that (a) blocked on participation, (b) produced no
finding, and (c) was structurally unable to prove the participation it was blocking on.
(c) is fixed. (a) and (b) together are the open question.

## The question for the epic

What must a REQUIRED bot produce for the block to be worth its cost? The current contract
gates on *participation*, and a summary-only bot satisfies participation by definition while
contributing nothing a merge decision depends on. Two shapes exist in the corpus already:

- `2026-09-03-23-003` — "Gate participation on a bot that read the diff, not on required-bot
  quorum alone." The evidence side of the same question.
- `2026-09-03-08-001` — "A bot status-summary body with no claim is stored as an actionable
  finding, driving `pct_resolved_as_fixed` to a false 0.0%." The storage side.

This candidate is the *composition* side: whether a bot whose only publish shape carries no
claim belongs in `required_bots` at all, or belongs there with a different predicate.

## Scope caveat (deliberate)

The zero-yield measurement is over ONE run on ONE PR. It is a datum, not a verdict — the
epic holds the cross-plan landings needed to say whether this bot's yield is zero in
general or zero here. Do not act on the composition question from this single observation;
corroborate against the epic's landing record first.

Source: plan `the-foreign-gate-population-and-branch-f-recovery`, PR #1473 (merged
`38af136ede5c7d6ea531a38d59a67ece1bf3ade2`).
