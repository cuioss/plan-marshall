envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:45:52Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# The one commit that fixed a review-caught defect was itself never reviewed

## Observation

PLAN-111's fix commit was produced in two rounds: `pr-agent` caught a real defect in round 1 (a lifetime-vs-current-cycle counter bug in the new self-response-loop guard), and TASK-004 corrected it. But the corrective commit — the one whose diff mattered most, because it fixed the bug an earlier review had just flagged — was never reviewed by any bot before merge:

- `coderabbit` (required reviewer) hard-rate-limited vendor-side for ~57 minutes, re-attempted, and refused again against the new HEAD.
- `sourcery` was over its weekly quota.
- `pr-agent` did not run against the fix commit at all — it had already reviewed and caught the round-1 defect on the prior HEAD, but nothing re-triggered it for the corrective commit.

The operator merged at the loop-back ceiling with zero bots having seen the corrective diff.

## Why it matters

This is a sharper instance of the epic's headline theme than "a reviewer was absent": it is specifically the **fix for a caught defect** that went unreviewed, meaning the loop that is supposed to catch a bad fix (review → fix → re-review) terminated one link short of its own closing link. A defect-fixing commit is exactly the commit type where an unreviewed merge carries the most residual risk, because it is the one most likely to introduce a new defect while removing an old one (as round 1 itself demonstrated).

## Corrective rule

When a PR reaches the loop-back ceiling and the outstanding, unreviewed commit is itself a **correction of a bot-caught defect** (not an unrelated late change), that should be flagged more prominently than an ordinary "proceeded unreviewed at ceiling" — e.g. a distinct disposition or a stronger operator-facing warning, since the review loop's own purpose (catch-then-verify-the-catch) did not complete.

## Recurrence context

Corroborates the epic's standing "review bots absent/rate-limited at the exact moment their check mattered" pattern (`project_pr_agent_third_reviewer.md`, the #1046 zero-comments-despite-green-check finding). This instance adds a new sub-shape: the missing review specifically targets the fix-of-a-caught-defect commit, not merely the final commit generically.
