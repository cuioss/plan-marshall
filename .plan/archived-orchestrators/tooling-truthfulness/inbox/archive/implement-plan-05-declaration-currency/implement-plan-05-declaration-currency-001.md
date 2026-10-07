envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-13T12:29:58Z

# Add bulk resolve to manage-findings for triage passes

## Context

Finalize triage of 11 `pr-comment` findings on plan
implement-plan-05-declaration-currency needed 11 single-hash
`manage-findings resolve` calls, one per finding, after the per-finding
triage dispositions were already decided.

## Root cause

`manage-findings resolve` addresses exactly one `--hash-id` per call, so
a triage pass that disposes a whole finding set pays one round-trip per
finding with no bulk form.

## Proposed action

Extend `manage-findings resolve` with a bulk form (repeatable `--hash-id`
or a `--type` plus `--resolution` filter) so a triage pass disposes a
finding set in one call.

## Evidence

- aspect: llm-to-script-opportunities — "resolve findings one hash at a time during triage", repetition 11, complexity low
- aspect: log-analysis — 274 manage-findings calls in the plan script log
