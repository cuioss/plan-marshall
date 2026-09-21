envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:51Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# No dispatch in the plan recorded its four context-load columns

## Context

Across all 21 dispatch-boundary rows — 1 in `4-plan`, 6 in `5-execute`, 14 in
`6-finalize` — every one records `input_tokens`, `output_tokens`,
`cache_read_input_tokens` and `cache_creation_input_tokens` as the literal
`unmeasured`. The `context_position_cost` block therefore reports:

```
total_rows: 21
measured_rows: 0
unmeasured_rows: 21
position_multiple: unmeasured
```

`manage-metrics enrich` was never run for this plan either, so
`billing_weighted_total` has `population_count: 0` and the `Billing (cost)`
column in `metrics.md` is empty on all six phase rows.

Net effect: a plan that spent 5,845,041 dispatched tokens over ~5 hours of worked
time produced no cache-read measurement anywhere, and no derived-cost figure at
all.

## Root cause

The four context-load flags on `record-dispatch-boundary` are optional and no
dispatch site passes them. The design is sound — an omitted flag correctly
writes `unmeasured` rather than a false `0` — but with no caller supplying them
the honest-absence path is the only path ever taken, so the measurement exists
in the schema and never in the data.

`enrich` is the other route to the same four fields, and it is not part of the
finalize step roster, so a plan gets the billing-weighted measure only if
someone runs it by hand.

## Proposed action

Either forward the dispatched agent's `message.usage` four-field view at each
`record-dispatch-boundary` call site, or make `enrich` a finalize step so the
per-phase four-field walk runs once per plan. Given that cache-read dominates
billing weight, a corpus in which `measured_rows` is 0 on every plan cannot
support any cost analysis at all.

## Evidence

- aspect: log_analysis — `context_position_cost.measured_rows: 0` of
  `total_rows: 21`; `by_phase` shows `unmeasured` for 4-plan, 5-execute and
  6-finalize alike
- aspect: plan_efficiency — `totals_billing_weighted_total: 0` with
  `totals_billing_weighted_total_population_count: 0`; `Billing (cost)` renders
  `-` on every phase row and on the Total
- artifact: every row of all three `work/metrics-dispatch-boundaries-*.toon`
  files carries four `unmeasured` columns
