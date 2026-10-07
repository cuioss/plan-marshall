envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:22Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high

# Pass the four context-load columns at every record-dispatch-boundary call

## Context

`record-dispatch-boundary` accepts four context-load columns: `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens` and `--cache-creation-input-tokens`. They have no numeric default, so an omitted flag writes the literal `unmeasured` - a deliberate design so that "the caller passed no measurement" stays distinguishable from "the dispatch loaded zero context".

On this plan, all 22 dispatch-boundary rows across 4-plan, 5-execute and 6-finalize record all four columns as `unmeasured`. `context_position_cost` reports `measured_rows: 0`, `unmeasured_rows: 22`, and `position_multiple: unmeasured`. No caller supplies them.

The consequence lands on the most expensive part of the plan. 6-finalize consumed 3,219,394 tokens - 60% of the plan total and 3.2x the whole execute phase - and there is no cost-per-context figure for any of it. `totals_billing_weighted_total` aggregates to `0` over `totals_billing_weighted_total_population_count: 0`.

A related half of the same gap: 8 of 16 finalize steps are classified `no_evidence` by `check-dispatch-audit`, matching exactly the steps whose `record-step` entries read `total_tokens=unmeasured`.

## Root cause

The recorder's four columns were added and documented, but no call site was updated to populate them. The honest `unmeasured` sentinel keeps the gap visible rather than hiding it as a zero, which is why it is diagnosable at all - but nothing closes it.

## Proposed action

Populate the four columns from the dispatched agent's `message.usage` view at every `record-dispatch-boundary` call site. Given that token reduction is a standing priority and cache-read dominates billing weight, a finalize phase this expensive with zero context attribution is the highest-value place to start measuring.

## Evidence

- fragment-log-analysis.toon `context_position_cost`: `total_rows: 22`, `measured_rows: 0`, `unmeasured_rows: 22`, `position_multiple: unmeasured`; every row's `unmeasured_columns` lists all four.
- `manage-metrics generate`: `totals_billing_weighted_total: 0`, `totals_billing_weighted_total_population_count: 0`.
- metrics.md: 6-finalize 3,219,394 tokens of 5,406,410 plan total.
- fragment-execution-context-dispatch-audit.toon: `dispatch_coverage` 7 dispatched / 1 inline / 8 no_evidence of 16.
