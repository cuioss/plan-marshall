envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:07:05Z

# Candidate lesson: script-failure cluster — build wrapper mislabels a 15s subprocess TIMEOUT as an argparse rejection

- source_signal: script_failure cluster (8 of 9 distinct notations)
- notation: `plan-marshall:build-pyproject:pyproject_build`
- markers: three `[ERROR] ... script_failure` lines (06:51, 14:49, 14:52), all identical

## What happened

`exit_code=2 failure_kind=argparse_rejection detail=Failed to invoke manage-status get-worktree-path for plan_id='plan-truth-148': Command '[... execute-script.py ... get-worktree-path --plan-id plan-truth-148]' timed out after 15 seconds`.

The invocation was CORRECT. The wrapper's internal `get-worktree-path` resolution subprocess exceeded a 15-second timeout — under heavy concurrent build load, visible in the surrounding log as multiple long-poll jobs with ETAs of 500-1300 seconds. The failure was then classified `argparse_rejection`, which it is not.

## Candidate rule

A misclassified failure kind sends every reader down the wrong diagnostic path: `argparse_rejection` says "fix your call", while the real cause is a resolution subprocess starving under build-server contention. Classify by the actual failure mode, and treat a hardcoded 15-second timeout on an internal resolution call as too tight for a machine that is concurrently running multi-minute builds. Three firings of the identical error is a load-dependent flake, not a call defect.
