envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:32Z

component=plan-marshall:manage-metrics
category=bug
created=2026-08-31
bundle=plan-marshall
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery

# Every dispatch-boundary row in this run recorded its four context-load columns as unmeasured

## Context

This plan spent at least 5,715,960 tokens and produced **no cache-read share and no billing-weighted figure at all**. Two independent instrumentation paths were both left uncalled:

1. **Per-dispatch context load.** All 18 `record-dispatch-boundary` rows — 1 in `4-plan`, 5 in `5-execute`, 12 in `6-finalize` — carry `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens` as the literal `unmeasured`. Every call site omitted the four flags. `context_position_cost` therefore reports `measured_rows: 0` of 18 and `position_multiple: unmeasured` for the whole plan.
2. **Per-phase four-field view.** `totals_billing_weighted_total` is `0` with `totals_billing_weighted_total_population_count: 0`, and every phase row reads `inline_main_context_tokens: unmeasured`. That is the signature of `manage-metrics enrich --session-id` never having run. The `Billing (cost)` column in `metrics.md` renders entirely blank.

The instrumentation behaved correctly — it reported `unmeasured` rather than fabricating zeros, and `unmeasured_context_load_columns` names exactly which columns declined to claim a value. What is missing is any caller passing the values.

The consequence is specific to this epic: `cache_read` share is the epic's declared top-priority cost lever, and a 5.7M-token plan contributed nothing measurable to it.

## Root cause

The four context-load flags on `record-dispatch-boundary` and the `enrich` call are both optional and both unwired at the dispatcher call sites. Nothing fails when they are omitted — the row is written, the report renders, and the only symptom is a blank column that reads like a zero.

## Proposed action

1. **Wire the four context-load flags at every `record-dispatch-boundary` call site** in `phase-5-execute` and `phase-6-finalize`, sourced from the dispatched agent's `message.usage` view at termination. The columns already exist and already distinguish measured-zero from unmeasured; only the producer is missing.
2. **Make `enrich` part of the finalize metrics close**, not an optional post-hoc verb — or, failing that, have `record-metrics` report `enrich_ran: false` in its `display_detail` so a blank Billing column is visibly unmeasured rather than silently blank.
3. Guard against the reading failure directly: `metrics.md` should render an unmeasured `Billing (cost)` total as `unmeasured`, never as `0`. A `0` in a cost column asserts a measurement nobody made and averages into every cross-plan roll-up as though the plan were free.

## Evidence

- aspect: plan_efficiency — `billing_column_unavailable` block; `totals_billing_weighted_total_population_count: 0`
- aspect: logging_gap_analysis — `CONTEXT_POSITION_COST` and `BILLING_COLUMN_UNMEASURED` gaps, both warning severity
- aspect: log_analysis — `context_position_cost`: `total_rows: 18`, `measured_rows: 0`, `unmeasured_rows: 18`, `position_multiple: unmeasured`
