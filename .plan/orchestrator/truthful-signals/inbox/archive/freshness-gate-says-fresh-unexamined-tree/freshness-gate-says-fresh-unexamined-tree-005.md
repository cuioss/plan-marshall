envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:20Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Run reconcile-ledgers at record-metrics and surface a non-zero findings_count

## Context

A run writes two independent token row-ledgers with no shared transaction and no
shared key: `execution.toon`'s `execution_log[]` (one row per `record-step`) and
`work/metrics-dispatch-boundaries-{phase}.toon` (one row per dispatch termination).

`manage-metrics reconcile-ledgers` exists precisely to compare them. Nothing in
`phase_6.steps` runs it — the manifest's 23 steps include `record-metrics` but no
reconciliation.

Run by hand against this plan, it returns **20 findings**:

- `union_rows: 29` against `execution_log_rows: 21` and `boundary_rows: 17` — neither
  ledger alone sees the run
- 7 `row_absent_from_execution_log` carrying **1364122 measured tokens** invisible to
  any execution-log sum
- 12 `row_absent_from_boundary_ledger` carrying 356042 measured tokens
- 1 `boundary_never_closed` — 12 rows / 2622668 tokens under a phase row with no
  `end_time`

One of those orphans is a **5-execute dispatch at 2026-09-06T11:52:27Z carrying
225374 tokens — roughly 16 hours after the 5-execute row was closed at
2026-09-05T19:46:21Z**, with `close_count` still 1 and `re_entered_phases` empty.

## Root cause

The reconciliation capability was built and then not wired into the lifecycle that
produces the divergence. Every plan writes both ledgers; no plan checks them against
each other; so the divergence is discoverable only by someone who already suspects it.

`record-metrics` (order 998) is the natural site: it is the authoritative close, it
already reads both stores, and a reconciliation there runs after the last row either
ledger will receive.

## Proposed action

1. Have `record-metrics` call `reconcile-ledgers` after its close and record
   `findings_count` plus the per-class counts on its step record `facts`.
2. Emit a `warning`-severity finalize finding when `findings_count > 0`, naming
   `union_rows` against each ledger's own row count — the union is the number a reader
   should take, and nothing currently says so at finalize time.
3. Treat `boundary_never_closed` as the specific signal that the phase's own summary
   was never recorded, distinct from an absent row.

## Evidence

- `manage-metrics reconcile-ledgers --plan-id freshness-gate-says-fresh-unexamined-tree` — `findings_count: 20`, `union_rows: 29`, `execution_log_rows: 21`, `boundary_rows: 17`
- aspect: manifest_decisions — `phase_6.steps[23]` contains `record-metrics` and no reconciliation step
- aspect: logging_gap_analysis — the 5-execute orphan at 2026-09-06T11:52:27Z, 225374 tokens
- work/metrics.toon — `re_entered_phases[0]` empty, 5-execute `close_count: 1`
