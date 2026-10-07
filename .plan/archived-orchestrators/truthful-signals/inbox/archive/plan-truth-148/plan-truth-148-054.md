envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:50Z

# Candidate lesson: the automatic-review step closed done with a refused-structural reviewer un-triaged

- source_signal: automatic-review / step outstanding state
- record: `automatic-review` step record, `display_detail: "0 comment(s) found - 1 reviewed, 1 empty, 1 refused-structural (triage pending)"`, outcome=done, firing_count 3
- resolution: outstanding at gate-evaluation time — this is what set `signal_automated_review_count=1`

## What happened

Of three configured reviewers, exactly ONE was measurable. The step recorded `outcome=done` with `0 comment(s) found` while its own detail names three distinct non-participation states: one reviewed, one returned empty, one was refused-structural with triage still pending. The review-retrospective recorded the same split independently: "1 of 3 reviewers measurable, 8 actionable comments".

The refusal cause is visible in the work log: a CodeRabbit re-review at head `c5ed864ce` was REFUSED by the re-trigger guard with `reason=window_open, holder=architecture-store-query-truthfulness, seconds_remaining=2444` — another plan held the rate window. The guard correctly did NOT re-issue, since re-issuing inside an open window only resets it.

## Candidate rule

`outcome=done` plus `0 comments found` is not "the reviewers were happy" — it is one measured reviewer and two that produced no signal. A review step's close must publish the per-bot participation split, and `(triage pending)` inside a `done` detail is a contradiction: a pending triage is outstanding work the record is reporting as complete. Cross-plan rate-window contention is the mechanism that most often produces this state, and it is invisible unless the refusal reason is surfaced on the step record rather than only in the log.
