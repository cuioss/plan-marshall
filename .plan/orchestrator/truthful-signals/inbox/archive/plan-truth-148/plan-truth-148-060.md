envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:06:59Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-change-ledger:manage-change-ledger

- source_signal: script_failure cluster (6 of 9 distinct notations)
- notation: `plan-marshall:manage-change-ledger:manage-change-ledger`
- marker: `manage-change-ledger.py: error: unrecognized arguments: --plan-id plan-truth-148`

## What happened

`--plan-id` was appended to a script that declares it NOWHERE — not on the router and not on any of its four verbs (`worktree-sha`, `append`, `classify-outcome`, `query`). The rejection names no position to move it to, because there is none.

## Candidate rule

The third case of the `--plan-id` trichotomy: some scripts do not take it at all, and for those the correct action is to append nothing. An "unrecognized arguments" rejection with no positional hint is the signature of this case — do not respond to it by moving the flag, which is the reflex the other two cases train.
