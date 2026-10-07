envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-15T06:25:13Z

# Finding: `automatic-review` step closes `done` with a refused-structural reviewer left un-triaged

- source: truthful-signals inbox message `plan-truth-148-054.md` (sender plan-truth-148, PR #1488)
- source_signal: automatic-review / step outstanding state

## What happened

Of three configured reviewers, exactly ONE was measurable. The step recorded `outcome=done` with
`0 comment(s) found` while its own `display_detail` names three distinct non-participation states: one
reviewed, one returned empty, one was refused-structural with triage still pending
(`"0 comment(s) found - 1 reviewed, 1 empty, 1 refused-structural (triage pending)"`). The review-retrospective
recorded the same split independently: "1 of 3 reviewers measurable, 8 actionable comments".

The refusal cause is visible in the work log: a CodeRabbit re-review at head `c5ed864ce` was REFUSED by the
re-trigger guard with `reason=window_open, holder=architecture-store-query-truthfulness,
seconds_remaining=2444` — another plan held the rate window. The guard correctly did NOT re-issue, since
re-issuing inside an open window only resets it.

## Candidate rule

`outcome=done` plus `0 comments found` is not "the reviewers were happy" — it is one measured reviewer and
two that produced no signal. A review step's close must publish the per-bot participation split, and
`(triage pending)` inside a `done` detail is a contradiction: a pending triage is outstanding work the
record is reporting as complete. Cross-plan rate-window contention is the mechanism that most often
produces this state, and it is invisible unless the refusal reason is surfaced on the step record rather
than only in the log.

## Why this belongs to review-apparatus, not truthful-signals

This is a PR-review-mechanics reliability defect (the `automatic-review` step's own close condition), not a
truthfulness-of-an-existing-report issue scoped to this epic's theme — per the epic's three-way routing
rule, PR/review-mechanics findings route to `review-apparatus`.
