envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:29Z

# Change-ledger recorded no build row for a plan with 37 build calls

## Metadata

- component: `plan-marshall:manage-change-ledger`
- category: bug
- confidence: high
- observed_in_plan: verdict-staleness-scoping

## Context

`analyze-logs` reads build time from the change-ledger, which it treats as the build-time
ORACLE. For this plan the ledger was present and readable and 796 rows were scanned, yet
`summed_rows: 0`, `build_count: 0` and `suspect_count: 0` — no build row for this plan at all.
The plan's own `script-execution.log` records 37 build-wrapper calls over the same window
(24 `pyproject_build`, 13 `build_server`), and eight build-result logs sit in the plan
directory.

## Root cause

Not yet established. The producer behaved correctly at the reporting boundary — it emitted the
literal `unavailable` sentinel rather than a `0`, and `build_count_reconciliation` states that
"the change-ledger holds no row for this plan, so the oracle build count is unmeasured rather
than zero". So the truthfulness machinery worked; what failed is upstream, in whatever writes a
build row to the ledger. Candidates worth checking in order: builds routed through the
`build_server` client may not append a ledger row at all (13 of the 37 calls took that path);
or the ledger row's plan attribution key does not match this plan.

## Proposed action

Determine which of the 37 build calls should have produced a ledger row and why none did.
Then add a reconciliation assertion so the divergence is caught at write time rather than
being discovered by a retrospective: when a plan's script log records build calls and its
ledger holds zero build rows, that is a recordable inconsistency, not a silent `unavailable`.

## Evidence

- aspect: plan_efficiency — `total_build_seconds: unavailable` with `ledger_present: true`, `ledger_readable: true`, `ledger_rows_scanned: 796`, `summed_rows: 0`
- aspect: log_analysis — `log_build_calls: 37`; `pyproject_build: 24`, `build_server: 13`
- source: eight `build-results/**/python-2026-09-22-*.log` files in the plan directory
