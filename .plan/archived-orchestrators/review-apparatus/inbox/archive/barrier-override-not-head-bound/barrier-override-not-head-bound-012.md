envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:37Z

# A finalize step re-fired after outcome=error emits no [DISPATCH] line

component: plan-marshall:phase-6-finalize
category: bug
confidence: high

## Context

`pre-submission-self-review` ran three times in this plan:

| Time (UTC) | Event |
|---|---|
| 08:43:44 | `[DISPATCH]` line emitted — the only one |
| 08:49:21 | `execution-context.pre-submission-self-review Complete` |
| 08:50:18 | `record-step` outcome=**error**, 219484 tokens |
| 09:39:21 | `execution-context.pre-submission-self-review Complete` (no `[DISPATCH]`) |
| 09:58:26 | `execution-context.pre-submission-self-review Complete` (no `[DISPATCH]`) |
| 10:00:08 | `record-step` outcome=executed, 212423 tokens |

Two envelopes ran with no dispatch evidence at all.

## Root cause

The `[DISPATCH]` emission is bound to the first-entry path of the step. The re-fire path after an
`outcome=error` re-enters the envelope without going back through the emission point, so the
dispatch-logging emission contract is satisfied once per step rather than once per envelope.

## Proposed action

Emit the `[DISPATCH]` line at every envelope entry, not per step. The line already carries `role` and
`workflow`; a re-fire is a distinct dispatch and must be observable as one. Without it, any consumer that
counts dispatches (the retrospective's dispatch audit, token attribution, dispatch-boundary accounting)
under-counts exactly the envelopes that failed — the ones most worth seeing.

## Evidence

- aspect: execution_context_dispatch_audit — `shape_violation` finding at work.log:210
- aspect: logging_gap_analysis — `phase-6-finalize,DISPATCH` gap
- aspect: plan_efficiency — the invisible re-fires account for 431907 tokens, 14.6% of whole-plan spend
- execution.toon `execution_log` — two `pre-submission-self-review` rows (error then executed) against one `[DISPATCH]` line
