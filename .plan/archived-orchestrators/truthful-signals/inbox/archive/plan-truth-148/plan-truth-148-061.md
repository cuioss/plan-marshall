envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:07:02Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-config:manage-config

- source_signal: script_failure cluster (7 of 9 distinct notations)
- notation: `plan-marshall:manage-config:manage-config`
- marker: `manage-config.py: error: unrecognized arguments: --plan-id ...`

## What happened

`--plan-id` was appended to `manage-config`, which declares 28 top-level verbs and does not accept it at the router. The failure fired inside the wait-region unified triage, immediately after the review-comment triage had added six fix tasks.

## Candidate rule

Same trichotomy member as the change-ledger cluster, and the two firing within the same run is the evidence that matters: the `--plan-id`-by-rote reflex accounts for three of this run's nine failure clusters (architecture, change-ledger, config). A single persona-level statement of the trichotomy — declared-before-verb, declared-after-verb, not declared — would have prevented all three.
