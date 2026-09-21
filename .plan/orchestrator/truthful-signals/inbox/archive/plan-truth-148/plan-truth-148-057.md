envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:06:50Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-files:manage-files

- source_signal: script_failure cluster (3 of 9 distinct notations)
- notation: `plan-marshall:manage-files:manage-files`
- marker: `[ERROR] ... script_failure ... Use --dir for ... list — declared: ['dir','plan-id']`

## What happened

`manage-files list` was invoked with a flag other than its two declared ones (`--dir`, `--plan-id`).

## Candidate rule

A two-flag verb has no room for extrapolation, and the rejection message already names the full declared set. The generalisable point is that the executor's rejection messages ARE the canonical reference — they print the declared flag list, so a single `--help` or one read of the rejection resolves the call, while guessing a second time costs another round trip.
