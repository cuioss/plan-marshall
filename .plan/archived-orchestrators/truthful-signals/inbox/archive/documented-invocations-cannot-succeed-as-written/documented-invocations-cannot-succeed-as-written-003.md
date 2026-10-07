envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:43Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# A finalize loop-back into phase-5 leaves no re-entry record on the phase row

## Context

This plan looped back from `6-finalize` to `5-execute`: `automatic-review` filed
7 pr-comment findings, triage opened fix tasks, phase-5 produced commits
`a4cdb8784` and `49769bd2f`, and the whole settle band re-fired.
`status.metadata.loop_back_iteration` is `1`.

Every other re-entry signal reports a plan that never looped back:

- `re_entered_phases: []` from `manage-metrics generate`
- the `5-execute` row's `close_count` is `1`, and `close_count > 1` is the
  documented AUTHORITATIVE re-entry marker
- the `5-execute` row's `end_time` is `2026-09-02T19:03:55Z`, while two of its
  dispatch-boundary rows are stamped `2026-09-03T10:54:29Z` and
  `2026-09-03T11:10:21Z`
- `returned_with_findings` is 0 across all 21 dispatch-boundary rows
- no step's `prior_firings` carries a `loop_back` outcome — the 16 finalize
  steps record only `done` and `failed`

## Root cause

The loop-back path re-enters phase-5 without calling `end-phase` /
`phase-boundary` on the way back out, so the row is never re-closed and
`close_count` never increments. The accounting consequence is real and was
caught only by a different mechanism: the row's own `total_tokens` (1,038,561)
is short of its dispatch-boundary total (1,323,927), and the reconciliation
preferred the larger measure, silently repairing a 285,366-token gap the
re-entry signal denied existed.

## Proposed action

Two independent repairs, both cheap:

1. Stamp the metrics phase boundary on the loop-back re-entry so `close_count`
   and `re_entered_phases` reflect it.
2. Add a `phase_reentry_undeclared` finding to `reconcile-ledgers`: any
   dispatch-boundary row timestamped later than its phase row's `end_time`
   while `close_count == 1`. It already reads both ledgers and already emits
   `boundary_never_closed`; this is one comparison more.

## Evidence

- aspect: plan_efficiency — metrics.md reconciliation note: "5-execute →
  dispatch_boundary_total 1,323,927 (> total_tokens 1,038,561)"
- aspect: logging_gap_analysis — `returned_with_findings: 0` across 21 rows;
  no `loop_back` outcome in any firing history
- artifact: `work/metrics-dispatch-boundaries-5-execute.toon` rows 5 and 6
  postdate the phase row's `end_time`
