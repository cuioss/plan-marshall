envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:07:08Z

# Candidate lesson: script-failure cluster — plan-marshall:phase-6-finalize:ci_complete_precondition

- source_signal: script_failure cluster (9 of 9 distinct notations)
- notation: `plan-marshall:phase-6-finalize:ci_complete_precondition`
- marker: `Add the required flag(s) to ... resolve: ['pr-number','worktree-path']`

## What happened

`ci_complete_precondition resolve` was invoked without its two REQUIRED flags, immediately after the push step completed and just before ci-verify. Both values were available in the plan record at the time (`pr_number: 1488`; the worktree path in metadata).

## Candidate rule

This is the missing-required-flag signature rather than the invented-flag one, and it is the more surprising of the two: the caller had both values in hand and omitted them. A precondition script that gates a phase transition should be called from a documented invocation block that names its required flags inline, so the values that are already resolved get forwarded rather than dropped.
