# WS-01: Measurement & Ledgers

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns the honesty of every derived number: ledger joins that pair by construction,
build telemetry that attributes instead of dropping, and retrospective aspects that
report measured populations rather than clean-looking zeros. Closed when every
count in the finalize lane carries its population and every ledger row has a join key.

## Scope

- In scope: manage-metrics ledgers, change-ledger rows, build-pyproject telemetry,
  plan-retrospective aspects, per-task artifact emission, lock accounting.
- Out of scope: gate verdicts and currency (WS-02/WS-08), reviewer-value signals (WS-03),
  footprint capture timing (WS-04).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-ledger-joins | shipped | Ledger pairing, context-load columns, retrospective aspects (#1545) |
| PLAN-02-build-telemetry | staged | Build attribution, locks, daemon and generator telemetry |

## Sequencing and Surface Notes

- PLAN-01 and PLAN-02 touch disjoint skill surfaces; both may run while no other
  WS-01 plan is launched (parallelization_scope=2).
- PLAN-01's ledger-join changes are read by WS-08's re-fire accounting; WS-08
  sequences after PLAN-01 lands.
