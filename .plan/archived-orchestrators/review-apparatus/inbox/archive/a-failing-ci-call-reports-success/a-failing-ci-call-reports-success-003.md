envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:42:39Z

# Cap or triage error-terminated finalize dispatches — 34% of finalize spend bought zero detection

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

8 of 33 recorded finalize dispatches terminated in a fatal `error`, consuming
2,189,320 tokens. Per the dispatch-boundary contract, an `error` row is genuinely
non-productive terminal waste — a findings-bearing loop-back is stamped
`returned_with_findings` instead, and this phase recorded 2 of those separately.
So the 2.19M is spend that examined nothing and returned nothing. It is 34% of the
phase's 6,435,116-token dispatch total.

Four of the eight errors cluster inside a 14-second window (17:29:10 to 17:29:23)
immediately followed by a `blocked_session_restart` row, which reads as one
infrastructure event costing four dispatches rather than four independent faults.

## Root cause

Two distinct causes are being folded into one bucket. `retryable_total_tokens` is
recorded as 0 because the `blocked_session_restart` row itself carried no tokens,
while the four errors it plainly caused are attributed to `error_total_tokens`.
The figure that names recoverable waste therefore reads zero on a run whose
largest single waste event was recoverable.

## Proposed action

Attribute an `error` row that falls inside the blast radius of an adjacent
`blocked_session_restart` / `harness_cancellation` to `retryable_total_tokens`,
so the two remedies stay separable. Separately, consider a per-step ceiling on
consecutive error-terminated re-dispatches before the step escalates rather than
re-firing — `pre-submission-self-review` recorded 5 `failed` outcomes across 12
firings with no such ceiling.

## Evidence

- aspect: logging_gap_analysis — 6-finalize distribution: 22 step_complete, 8 error, 2 returned_with_findings, 1 blocked_session_restart
- aspect: logging_gap_analysis — `error_total_tokens: 2189320`, `retryable_total_tokens: 0`
- aspect: plan_efficiency — 6-finalize is the dominant phase at 6,435,116 tokens (59% share), outspending 5-execute 2.0x
