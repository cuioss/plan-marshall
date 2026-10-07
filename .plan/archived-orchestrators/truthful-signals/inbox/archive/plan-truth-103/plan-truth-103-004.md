envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:00:43Z

# Every dispatch-boundary row omitted its four context-load columns

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: plan-truth-103
source_aspects: log_analysis, logging_gap_analysis

## Context

`manage-metrics record-dispatch-boundary` accepts four per-dispatch context-load
flags — `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`,
`--cache-creation-input-tokens` — and deliberately writes the literal
`unmeasured` (never `0`) when they are absent, so that "the caller passed no
measurement" stays distinguishable from "the dispatch loaded zero context".

On plan-truth-103, **28 of 28** boundary rows across `4-plan`, `5-execute` and
`6-finalize` carry `unmeasured` in all four columns. `context_position_cost`
consequently reports:

```
total_rows: 28
measured_rows: 0
unmeasured_rows: 28
position_multiple: unmeasured
position_multiple_basis: unmeasured
```

Separately, `manage-metrics enrich` was never invoked for this plan:
`totals_billing_weighted_total: 0` with
`totals_billing_weighted_total_population_count: 0`, every phase row carries
`inline_main_context_tokens: unmeasured`, and the `Billing (cost)` column in
`metrics.md` renders as a dash for all six phases.

## Why it matters here specifically

This was a 6,957,415-token plan (a FLOOR — `6-finalize` never closed) that
crossed its `broad + bug_fix` **error** anchor by 2.8x. It is exactly the run
where one would want to know where the context load went. The two mechanisms
built to answer that — the per-dispatch context-load columns and the per-phase
normalized `enrich` view — are both completely empty.

The instrumentation is correct and honest: it says `unmeasured` rather than
inventing zeros. The gap is entirely on the producer side. Nobody passes the
flags, and nobody calls `enrich`.

## Proposed action

1. Make the finalize dispatcher forward the four context-load figures it already
   receives in each agent return into its `record-dispatch-boundary` call — the
   same place it already forwards `--total-tokens` / `--tool-uses` /
   `--duration-ms`.
2. Call `enrich --plan-id {plan_id} --session-id {session_id}` once at
   `record-metrics` time. The session id is already captured in
   `status.metadata.session_ids`, so the input exists.
3. Consider making `generate` report `measured_rows: 0 of N` as a **finding**
   rather than a field, so a whole-plan measurement gap is visible without
   reading the sub-block.

## Evidence

- aspect: log_analysis — `context_position_cost: {total_rows: 28, measured_rows: 0, unmeasured_rows: 28, position_multiple: unmeasured}`
- aspect: log_analysis — every `dispatch_boundaries` row lists all four columns under `unmeasured_columns`
- `work/metrics.toon` — `totals_billing_weighted_total: 0`, `totals_billing_weighted_total_population_count: 0`
- `work/metrics.toon` — all six rows carry `inline_main_context_tokens: unmeasured`
- `metrics.md` — `Billing (cost)` column is `-` on all six phases and on the Total
