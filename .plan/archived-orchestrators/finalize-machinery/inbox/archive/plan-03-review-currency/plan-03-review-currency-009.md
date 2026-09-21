envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T19:29:20Z

component=plan-marshall:phase-5-execute
category=improvement
created=2026-09-17
bundle=plan-marshall

# Document the fix-task loop-back dispatch shape (no envelope)

Loop-back fix tasks allocated by triage carry no `envelope_id`, `cost_size`,
or `predicted_cost_tokens` — the envelope protocol assumes plan-time packing
that never ran for them. The loop-back continuation section prescribes
re-dispatch against the fix tasks but never states the envelope fields for
that dispatch, forcing the orchestrator to improvise (dispatch with
`task_number` and no `envelope_id`, which the executor tolerates).

## Proposal

State the fix-task dispatch shape explicitly in the loop-back continuation
contract: which envelope fields are carried, which are omitted, and that the
executor runs pending tasks when no envelope group is assigned.

## Evidence

Plan plan-03-review-currency, loop-back iteration 1: TASK-4..8 all showed
`envelope_id: null`; five single-task dispatches with `task_number` only all
completed cleanly.
