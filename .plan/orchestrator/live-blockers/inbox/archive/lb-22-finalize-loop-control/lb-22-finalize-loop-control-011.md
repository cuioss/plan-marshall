envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:10Z

component=plan-marshall:plan-marshall
category=improvement
source_plan=lb-22-finalize-loop-control
confidence=high

# Store a wrong bot comment as rejected so review statistics count it

## Context

cuioss-review-bot left one inline suggestion on PR #1718 (`094626`, `_cmd_mark_step.py:689`, self-rated importance 9). Triage read the code and found the claim wrong: two branches above the flagged check already return for every same-outcome re-call, so the suggested condition would change nothing. The finding was resolved `accepted`, with a detail that opens "False positive, no change made".

The review retrospective reads the resolution, not the detail. It reported the reviewer as 0 fixed, 1 accepted, 0 rejected, and zero false positives for the PR. The one measured thing this reviewer contributed was a wrong high-confidence suggestion, and the statistic records the opposite.

## Root cause

The triage workflow offers `accepted` as its only disposition for a finding that is neither fixed nor suppressed. "The reviewer is right but we will not change it" and "the reviewer is wrong" are stored under the same value, and the second is the one the reviewer comparison exists to count.

## Proposed action

- Give triage a distinct disposition for a claim judged wrong (the aggregator already has a `rejected` column) and use it in the batched-decision branch of `triage.md`.
- Apply the same value to the bot-acknowledgement case if it keeps being stored: it is not an accepted gap either.

## Evidence

- aspect: chat_history_analysis - triage hand-back: "094626 is stored as accepted because that is the workflow's only non-fix, non-suppress disposition".
- review retrospective hand-back: "Mis-triage flagged: the finding is resolved accepted, not rejected ... The aggregator therefore reports 0 false positives for this PR, which understates it."
- plan artifact: `review-retrospective.md` in the plan directory.
