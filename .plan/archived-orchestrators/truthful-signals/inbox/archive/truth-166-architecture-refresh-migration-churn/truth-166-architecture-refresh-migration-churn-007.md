envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:33Z

component=plan-marshall:manage-metrics
category=improvement
confidence=high
rank=7
source_plan=truth-166-architecture-refresh-migration-churn

# Wire the context-load flags the recorder already accepts at the dispatch-return sites

## Context

This plan's entire cost-attribution surface is empty on the one axis the project ranks
first. Concretely:

- All **13** dispatch-boundary rows across `4-plan`, `5-execute` and `6-finalize` carry
  `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
  `cache_creation_input_tokens` as `unmeasured` — **0 of 13 measured** — so
  `context_position_cost.position_multiple` is `unmeasured` plan-wide.
- `manage-metrics enrich` never ran, so `totals_billing_weighted_total` is `0` at
  `totals_billing_weighted_total_population_count: 0`, and the `Billing (cost)` column in
  `metrics.md` is empty for all six phases.
- **27 of 32** execution-log rows carry no token figure, and every
  `manage-execution-manifest:record-step` decision entry reads
  `total_tokens=unmeasured, tool_uses=unmeasured`.

The run cost 9,322,722 dispatched tokens — itself a floor at `n=5/6` — with finalize alone
at 4,943,158 (53%). The cache-read share, documented as the dominant component of billing
weight, is unknown at both the per-dispatch and the per-phase tier.

## Root cause

The instrumentation is not missing and is not dishonest: `record-dispatch-boundary`
declares all four flags and deliberately writes the literal `unmeasured` rather than a
false `0`, and `unmeasured_context_load_columns` names exactly what each row declined to
claim. The gap is that **no call site passes them**. Similarly, nothing in the finalize
order runs `enrich`, so the per-phase normalized view is never populated.

## Proposed action

1. Pass the four context-load flags at the finalize and execute dispatch-return sites
   that already call `record-dispatch-boundary`.
2. Either run `enrich` from `record-metrics`, or render the `Billing (cost)` column as
   `unmeasured` rather than blank so an absent measurement is visible as one.
3. Pass token/tool figures at the `record-step` call sites, or have that verb read the
   accumulator the way `end-phase` already does.

## Evidence

- aspect: log_analysis — `context_position_cost: total_rows: 13, measured_rows: 0,
  unmeasured_rows: 13`; every phase row reads `cache_read_per_tool_use: unmeasured`.
- aspect: routing_decisions — `execution_log_rows_measured: 5`,
  `execution_log_rows_unmeasured: 27` of 32.
- `manage-metrics generate` — `totals_billing_weighted_total: 0`,
  `totals_billing_weighted_total_population_count: 0`.
- decision.log — every `record-step` line carries `total_tokens=unmeasured`.

## Generalizes

An instrument that is correctly built, correctly honest about its own absence, and never
called is indistinguishable in outcome from one that was never built — except that it
reports its silence in a vocabulary nobody is reading. When the measured axis is the
project's stated first priority, a 0-of-13 fill rate is the finding, not the `unmeasured`
literal that faithfully records it.
