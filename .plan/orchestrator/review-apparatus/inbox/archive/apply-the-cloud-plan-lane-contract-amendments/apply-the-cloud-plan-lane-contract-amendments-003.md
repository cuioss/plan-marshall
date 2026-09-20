envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:36Z

component=plan-marshall:phase-6-finalize
category=improvement
status=active

# The last remediation commit in a finalize chain ships reviewed by nothing but verify

## Context

Commit `30b325984` on plan `apply-the-cloud-plan-lane-contract-amendments` (16 insertions / 17 deletions — the over-claim deletions that fixed self-review round 6's own two findings) was reviewed by **nothing except `verify`**. No bot review, no self-review round. It merged in PR #1416 as part of `5f810002571fc98f86479527be96c46391d630d3`.

This is not an oversight in the run's judgement — the decision was reasoned and recorded at the time. But the shape it produces is structural: whatever the last remediation commit is, it ships unreviewed.

## Root cause

The review chain is unbounded by construction. A review produces findings; fixing them produces a commit; that commit would itself want reviewing; and at roughly one CodeRabbit review per hour under 8-PR per-developer-allowance contention, the regress has no natural terminus. The run resolved it by simply stopping, which is the only currently-available move, and the residue is one unreviewed commit per plan.

## Proposed action

Give the chain a bounded terminus instead of an unbounded regress: after the final remediation commit, run **one** mandatory self-review pass scoped strictly to the residual delta since the last reviewed head, with no further chaining permitted regardless of what it finds (findings from that terminal pass are filed, not fixed-and-re-reviewed). That closes the sliver at the cost of exactly one bounded pass, and it makes the terminal state explicit rather than a judgement call made under time pressure.

Note the self-referential hazard: this plan's own round 6 found 2 real defects inside the CodeRabbit remediation, so the class of defect a terminal pass would catch is demonstrated, not hypothetical.

## Evidence

- decision.log 2026-09-05T00:56:30Z — "The three commits since (352525f9, c57a294c, 30b325984) are the remediation of its own findings plus two defects self-review found IN that remediation; CodeRabbit has NOT reviewed them ... Not chaining further: each review can produce fixes that would themselves want reviewing, and at roughly one review per hour under 8-PR contention that regress is unbounded."
- decision.log 2026-09-05T03:35:45Z — "GENUINE RESIDUE ... commit 30b325984 ... was reviewed by NOTHING except verify. No bot review, no self-review round ... That is the unreviewed sliver of this change, and it is now merged."
- aspect: request_result_alignment — the two post-outline tasks TASK-007/008 both originate from review feedback, so the remediation chain is the norm on a reviewed plan, not an exception
