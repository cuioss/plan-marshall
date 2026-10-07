envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:14:01Z

# Candidate lesson: only 8 of 31 metrics ledger rows pair across the two stores, and the 6-finalize phase row understates its own dispatch spend by >=1.5M tokens

**Component**: `plan-marshall:manage-metrics`
**Source signal**: plan-retrospective report, re-derived first-hand in lessons-capture
**Suggested category**: bug

## Claim

`manage-metrics` keeps two row ledgers — the `record-step` execution log and the dispatch-boundary ledger — and they almost never agree. On this plan, the reconciliation reports **23 findings over a 31-row union**, with only **8 rows paired**. The `metrics.md` phase row for `6-finalize` is generated from the execution-log side, so every boundary row with no execution-log twin is spend that no phase total can see.

## Evidence (first-hand, `manage-metrics reconcile-ledgers`, run in this step)

```text
findings_count: 23
union_rows: 31
execution_log_rows: 25
boundary_rows: 14
```

Per-phase pairing:

| Phase | execution_log_rows | boundary_rows | paired_rows | union_rows |
|---|---|---|---|---|
| 4-plan | 0 | 1 | 0 | 1 (structurally_excluded) |
| 5-execute | 5 | 3 | **1** | 7 |
| 6-finalize | 20 | 10 | **7** | 23 |

Eight paired rows out of a 31-row union — **74% of rows exist in exactly one store**.

Two distinct defect shapes ride that gap, and the reconciler already names them apart:

- `row_absent_from_execution_log` — *"a dispatch terminated and recorded its usage, but no record-step row names it in the window — this spend is invisible to any execution_log sum"*. Four such rows: 6-finalize carries **221,480 + 187,333 + 82,919 = 491,732 tokens**, 5-execute a further **310,257**. That is **802K tokens of measured, attributed spend that no phase total includes**.
- `boundary_never_closed` — 6-finalize: *"10 dispatch-boundary row(s) recorded but the phase row carries no end_time"*, carrying **1,579,116 tokens**. The rows are present; nothing closed the phase, so its own summary of them was never computed.

## Why it matters

Both failures move the number in the **same direction — down**. A phase whose boundary was never closed and whose dispatch rows never paired reports a confident, well-formed, small figure. Nothing in `metrics.md` marks the row as partial, so the understatement is invisible at the point of consumption; you have to run a separate reconciliation verb to discover that the headline was assembled from a quarter of the rows.

This is the epic's own theme applied to the instrument the epic uses to measure itself: **a confident signal hiding a caveat**. Every token-roadmap figure derived from per-phase rows inherits it.

## Suggested directive (for the orchestrator to judge)

1. **`metrics.md` must publish its own pairing state.** A phase row generated over an unreconciled ledger should carry the population it was computed from (`paired / execution_log_only / boundary_only`) beside the total, so a reader sees `6-finalize: X tokens (7 of 23 rows paired)` rather than a bare `X`. A total whose denominator is unstated is not publishable — the project already enforces this for `corpus` counts and `inbox list` zeros.
2. **Fix `boundary_never_closed` at the writer, not the reader.** A phase with 10 boundary rows and no `end_time` means the close never fired. Establish whether the close is missing, racing, or being skipped on a particular termination path.
3. **Decide whether `row_absent_from_boundary_ledger` is a defect at all.** The reconciler's own detail text says it may be *"a declared exclusion class"* — but it does not say WHICH, so every one of the 17 such rows reads as ambiguous. Publish the exclusion classes as data so the finding can distinguish "excluded by design" from "write was missed"; today a reader cannot, and the 17 ambiguous rows swamp the 4 unambiguous ones.

Do not treat the figures above as stable: they were re-derived during finalize and moved between the retrospective's read (30-row union) and this one (31-row union) as later steps recorded. Re-derive before acting.
