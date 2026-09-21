envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T08:57:44Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# Populate the four context-load columns and run enrich at the metrics close

## Context

This plan has no four-field cost attribution from either of the two independent sources that exist to provide it — on a plan whose own subject is budget attribution.

- Per-dispatch: all 19 dispatch-boundary rows across 4-plan, 5-execute and 6-finalize carry `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens` as the literal `unmeasured`. `context_position_cost.measured_rows` is `0/19`; `position_multiple` is `unmeasured` for the whole plan.
- Per-phase: `manage-metrics enrich` was never invoked, so `totals_billing_weighted_total` is `0` with `totals_billing_weighted_total_population_count: 0`, and every phase row carries `inline_main_context_tokens: unmeasured`.

The `Billing (cost)` column of `metrics.md` is therefore empty for all six phases, and the plan's 5.99M dispatched tokens have no cost figure beside them.

Both channels already exist and are declared. `record-dispatch-boundary` declares all four flags. `enrich` is a documented verb. Neither is a missing capability; both are uncalled.

## Root cause

The four context-load flags are optional on `record-dispatch-boundary` and no dispatcher call site passes them — correctly writing `unmeasured` rather than a false `0`, which is why the gap is visible at all rather than silently reading as zero cost. `enrich` has no scheduled call site in the finalize step sequence; it is left to a caller who never runs.

## Proposed action

1. Pass the four `message.usage` values at every `record-dispatch-boundary` call site — the dispatcher already holds the returning agent's usage envelope when it stamps the row.
2. Invoke `manage-metrics enrich --plan-id P --session-id S` as part of the finalize metrics close, before `record-metrics` performs the authoritative phase close.

Both are call-site changes over existing verbs; neither needs new script surface.

## Evidence

- aspect: log_analysis — `context_position_cost: total_rows 19, measured_rows 0, unmeasured_rows 19`; every row lists all four columns under `unmeasured_columns`
- aspect: plan_efficiency — `totals_billing_weighted_total: 0`, `population_count: 0`; `Billing (cost)` column empty for all 6 phases
- aspect: logging_gap_analysis — both channels reported as one combined gap
