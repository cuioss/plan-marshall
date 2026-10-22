envelope_version=1
sender_type=plan
sender_id=lb-49-opencode-measurement
epic=live-blockers
kind=candidate-lesson
created=2026-10-22T11:23:19Z

# Build rows in the change ledger must carry a duration

## Context

`analyze-logs` compared the plan's 211 logged build calls against the change
ledger: ledger present and readable, 3990 rows scanned, but only 4 `kind=build`
rows for this plan — and all 4 carried `duration_seconds` of `0`/absent, so
`total_build_seconds` came back as the literal `unavailable` with
`summed_rows: 0`.

At the same time the script cost rollup attributes 62.6% of the plan's total
script time (40880s of 65256s) to
`plan-marshall:build-pyproject:pyproject_build`, with 181 calls and a 1373s
maximum. Build is the single largest time consumer in the plan and the one
figure the retrospective cannot report.

## Root cause

The build path appends a ledger row without the timing it already has in hand,
and the verify/quality-gate wrapper re-enters often enough that most calls never
reach an append at all. The consumer-side rule was already fixed: the producer
now emits `unavailable` rather than `0`, which is correct — but it converts an
invisible zero into a visible hole instead of closing it.

## Proposed action

Stamp `duration_seconds` (and `status`) on every `kind=build` ledger append from
the build wrapper's own measured wall time, including the in-process path that
currently appends nothing. Then a plan's build cost is a read, not a
reconstruction from log line timings.

## Evidence

- aspect: log_analysis — `build_time`: ledger_rows_scanned 3990, build_count 4, suspect_count 4, summed_rows 0, total_build_seconds unavailable
- aspect: log_analysis — `build_count_reconciliation`: log_build_calls 211 vs ledger_build_count 4, agreement `log_exceeds_ledger`
- aspect: log_analysis — `script_cost_rollup`: pyproject_build 181 calls, 40880210 ms, 62.645% share
- aspect: plan_efficiency — `totals.total_build_seconds: unavailable`, surfaced verbatim per the suspect-zero rule
