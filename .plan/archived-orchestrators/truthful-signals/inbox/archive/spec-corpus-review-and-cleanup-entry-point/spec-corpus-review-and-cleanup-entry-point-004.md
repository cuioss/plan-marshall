envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:17:24Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=spec-corpus-review-and-cleanup-entry-point
source_aspects=log_analysis,plan_efficiency

# Per-dispatch context-load columns unrecorded, so billing composition is unavailable

## Context

`record-dispatch-boundary` accepts four context-load columns — `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` — appended at the end of every dispatch-boundary row. Across this plan's three dispatching phases, **25 of 25 rows carry all four as unpopulated**:

```
context_position_cost:
  total_rows: 25
  measured_rows: 0
  unmeasured_rows: 25
  by_phase: 4-plan 1/0 measured, 5-execute 4/0, 6-finalize 20/0
  position_multiple: unmeasured
```

The 24 rows written between 2026-08-09 and 2026-08-10 report the four columns as `indeterminate`; the single row written on 2026-08-22 reports them as `unmeasured`. The same absence shows at the phase level: `manage-metrics generate` returns `totals_billing_weighted_total: 0` with `totals_billing_weighted_total_population_count: 0`, and `metrics.md` renders the `Billing (cost)` column as `-` for all six phases.

## Root cause

The recorder accepts the four columns but the dispatch-boundary call sites are not passing them. `enrich` — the other producer of the four-field view, which walks subagent transcripts — evidently also did not run or found nothing for this plan, so neither the per-dispatch nor the per-phase path populated a single value.

## Why this matters

The four-field view is the *only* source of the input/output split and the cache fields; the single-figure `<usage>` return tag carries neither. Without it:

- `billing_weighted_total` cannot be computed, so cost cannot be separated from work. This plan reports 5,432,972 dispatched tokens with no way to say what that cost.
- `position_multiple` — the cache-read-per-tool-use figure that measures what re-reading resident context costs as a dispatch grows — is `unmeasured` for every phase.

For a plan that spent 3.2M tokens in finalize alone, the composition of that spend is precisely the quantity a token-reduction effort needs, and it is exactly the quantity that was not recorded.

## Proposed action

1. Populate the four columns at every `record-dispatch-boundary` call site from the dispatched agent's `message.usage` view at termination. The recorder's argparse surface already accepts them and defaults them to 0 — which is itself worth revisiting, since a defaulted `0` is indistinguishable from a measured `0`.
2. Confirm whether `enrich` ran for this plan; if it did and produced nothing, the transcript-walk path needs its own investigation.
3. Keep the current honest labelling — `indeterminate` and `unmeasured` are correctly distinguished from a measured zero, and `totals_billing_weighted_total_population_count: 0` correctly publishes the empty population. The reporting is right; the measurement is missing.

## Evidence

- aspect: log_analysis — `context_position_cost.measured_rows: 0` over `total_rows: 25`; every row's `indeterminate_columns` lists all four fields
- aspect: plan_efficiency — `Billing (cost)` empty for all six phases; `totals_billing_weighted_total: 0` with `population_count: 0`
- corroborating: the dispatch-boundary rows are otherwise complete — 25 rows with correct `termination_cause`, `total_tokens`, `tool_uses` and `duration_ms`, so the recorder is being called; only the four appended columns are unfed
