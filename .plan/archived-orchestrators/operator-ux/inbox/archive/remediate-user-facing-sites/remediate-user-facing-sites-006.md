envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:41:40Z

component=plan-marshall:phase-5-execute
category=improvement
confidence=high
source_plan=remediate-user-facing-sites

# Forward the four context-load columns at every record-dispatch-boundary call site

## Context

`manage-metrics record-dispatch-boundary` declares four context-load columns — `input_tokens`,
`output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` — and writes the literal
`unmeasured` into any one its caller does not supply. On this plan, all 34 rows across `4-plan`,
`5-execute` and `6-finalize` carry `unmeasured` on all four. No dispatch site forwards them.

The consequences are visible downstream and they are not cosmetic. `context_position_cost` reports
`measured_rows: 0` and `position_multiple: unmeasured` for the whole plan. `billing_weighted_total`
is `0` with `totals_billing_weighted_total_population_count: 0`, so `metrics.md` renders the
`Billing (cost)` column as `-` for every phase and the Total.

The result is that an 8.5M-token plan produced no cost-versus-work comparison at all. The two
questions — how much dispatched work was done, and what it cost to buy — are deliberately kept
separate by the metrics design, and only one of them was answerable here.

The four-way reader contract (`measured` / `unmeasured` / `unrecognised` / `indeterminate`) worked
exactly as designed: nothing claimed a false zero, and the absence is legible. The defect is that
the producing side never fills the columns the contract exists to describe.

## Root cause

The columns were added to `record-dispatch-boundary` as optional-with-no-default, correctly, so that
"the caller passed no measurement" stays distinguishable from "the dispatch loaded zero context".
The call sites in `phase-5-execute` and `phase-6-finalize` were never updated to pass the values,
and because the absence is a valid state rather than an error, nothing complained.

## Proposed action

Forward the four `message.usage` fields at every `record-dispatch-boundary` call site — the
`phase-5-execute` per-task loop and the `phase-6-finalize` per-step dispatcher are the two that
matter, since together they wrote 33 of this plan's 34 rows. The values are already available to the
caller from the returned dispatch envelope; nothing needs to be computed.

## Evidence

- aspect: logging_gap_analysis — gap row: 34 of 34 rows unmeasured on all four columns;
  `context_position_cost.measured_rows: 0`, `unmeasured_rows: 34`, `position_multiple: unmeasured`.
- aspect: log_analysis — every row in `dispatch_boundaries` for `4-plan`, `5-execute` and
  `6-finalize` lists all four names under `unmeasured_columns` with `unrecognised_columns[]` and
  `indeterminate_columns[]` empty.
- aspect: plan_efficiency — `totals_billing_weighted_total: 0` with `population_count: 0` against
  `totals_tokens: 8481783`.
