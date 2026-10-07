envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:50Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# Phase-5 dispatches record usage at termination but no record-step row names them

## Context

`manage-metrics reconcile-ledgers` reports, for `5-execute`:

```
execution_log_rows: 0
boundary_rows: 6
union_rows: 6
```

with all six boundary rows classified `row_absent_from_execution_log` —
"a dispatch terminated and recorded its usage, but no record-step row names it in
the window; this spend is invisible to any execution_log sum". The six rows carry
1,323,927 tokens.

This is NOT the benign structural case. The same call correctly reports `4-plan`
as `structurally_excluded` because the execution log's writer does not accept
that phase — which shows the discriminator working, and shows that `5-execute`,
which the writer DOES accept, is a genuine gap.

## Root cause

Phase-5 calls `record-dispatch-boundary` on every dispatch termination but does
not call `record-step` for its own work, so one of the two row ledgers is empty
for the whole phase while the other is complete.

The consequence is a live wrong number, not a theoretical one:
`check-routing-decisions` reports

```
cost_preview:
  execution_log_tokens: 2710183
  execution_log_population: "5-execute,6-finalize"
```

The population string claims both phases; the figure covers `6-finalize` alone
and understates the plan by 1,323,927 tokens — about 23% of its total spend.

## Proposed action

Emit `record-step` rows for phase-5 dispatches, or — if phase-5 is deliberately
outside the execution log's population — declare it in the writer's accepted set
the way `4-plan` is declared, so `reconcile-ledgers` reports it as
`structurally_excluded` and no consumer builds a population string that promises
coverage the ledger does not have.

## Evidence

- aspect: logging_gap_analysis — `reconcile-ledgers` `5-execute` state
  `evaluated`, 6 findings, all `row_absent_from_execution_log`
- aspect: routing_decisions — `cost_preview.execution_log_tokens: 2710183` under
  `execution_log_population: "5-execute,6-finalize"`
- contrast: `4-plan` reported `structurally_excluded` with an explicit reason,
  proving the honest branch exists
