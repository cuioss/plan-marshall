envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T13:05:38Z

# The metrics Worked column excludes dispatched-leaf duration and under-reports agent work by up to 6.6x

- **component**: `plan-marshall:manage-metrics`
- **category**: improvement
- **severity**: warning
- **confidence**: medium
- **source**: plan-retrospective of `plan-less-pr-can-be-opened-but-never-corrected` (PR #1065)

## The discrepancy

`metrics.md` Phase Breakdown for this plan:

| Phase | Worked (reported) | Sum of dispatch-boundary `duration_ms` | Ratio |
|---|---|---|---|
| 5-execute | 47m47s | **5h16m** (18,994,920 ms over 11 rows) | 6.6x |
| 6-finalize | 50m9s | **1h24m** (5,032,979 ms over 13 rows) | 1.7x |

The dispatch-boundary figures come from
`work/metrics-dispatch-boundaries-{phase}.toon`, which the orchestrator already writes
after every dispatch termination, with `duration_ms` per row.

## Why it matters

`Worked` sits beside `Reported (wall)` and `Idle` in a table whose evident purpose is to
separate real effort from waiting. A reader takes `Worked 47m47s` to mean *"the system
spent 48 minutes working on phase 5"*. The dispatched leaves self-reported 5h16m. The
column is measuring orchestrator-context elapsed time and silently excluding the leaf
dispatches where nearly all the work happens.

This is the same family as the token accounting, which **was** fixed — `metrics.md`
already carries:

> Tokens reconciled from dispatch boundaries (same-population max, recovers accumulator
> under-count): 5-execute, 6-finalize

Tokens learned to read the dispatch-boundary file. Durations did not.

## Suggested direction

Apply the reconciliation that already exists for `total_tokens` to `duration_ms`: take the
same-population max (or sum, per the intended semantics) of the per-dispatch durations
against the orchestrator-derived worked time. The file, the field, and the reconciliation
pattern are all already in place — only the duration arm is missing.

If the two figures are meant to measure different things, the column needs a name that
says so; `Worked` currently over-claims.
