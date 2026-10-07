envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:35:05Z

component=plan-marshall:manage-metrics
category=bug
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# reconcile-ledgers' union_rows is not invariant under its own --window-seconds

## What happened

`manage-metrics reconcile-ledgers` was run twice over the **same, unchanged** pair of
ledgers for plan `disjointness-gate-reads-declared-surface-wrong`, varying only
`--window-seconds`:

| `--window-seconds` | findings | `union_rows` | 6-finalize `paired_rows` |
|---|---|---|---|
| 300 (default) | 24 | 34 | 9 |
| 900 | 20 | 32 | 11 |

The change is **not** monotonic pairing. The orphan sets **reshuffle**: at 300s the
`row_absent_from_boundary_ledger` set names `lessons-housekeeping`,
`architecture-refresh`, `ci-verify` and `branch-cleanup`; at 900s those four pair and
`push`, `project:finalize-step-review-retrospective` and an earlier
`pre-submission-self-review` row become orphans instead.

## Why it matters

The skill's own contract nominates `union_rows` as the authoritative figure:

> The result therefore publishes `union_rows` per phase and in total: that is the
> count a reader should take, and nothing else says so.

That figure moved from 34 to 32 with no change to either ledger. The number the
contract tells a reader to trust is a function of a tunable with no principled value,
so no run's reconciliation is reproducible unless the window is quoted alongside it.

The contract already names the cause:

> The join is on phase plus a timestamp window (`--window-seconds`, default 300),
> because the missing `step_id` leaves no other key.

A reconciliation built to adjudicate a divergence between two ledgers is itself
adjudicating by heuristic.

## Concrete instance

The `pre-submission-self-review` boundary row at `20:46:49Z` (181,354 tokens) and the
`record-step` row at `20:52:39Z` (181,354 tokens) are the **same dispatch**, 350
seconds apart. At the 300s default they are reported as **two** findings, one in each
direction — an orphan in the boundary ledger and an orphan in the execution log — for
a dispatch that both ledgers recorded correctly.

## Remedy shape

Write `step_id` onto the dispatch-boundary row at the `record-dispatch-boundary` call
site (the context is already in scope there). The join then becomes exact,
`union_rows` becomes window-invariant, and `--window-seconds` stops deciding the
answer.
