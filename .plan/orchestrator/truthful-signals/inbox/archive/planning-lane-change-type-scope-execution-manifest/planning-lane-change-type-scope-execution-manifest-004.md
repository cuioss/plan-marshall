envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T16:00:33Z

# Every dispatch-boundary row records its token decomposition as unmeasured

component: plan-marshall:manage-metrics
category: bug
confidence: high
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

This plan wrote 68 dispatch-boundary rows: 1 in `4-plan`, 6 in `5-execute`, 61 in `6-finalize`. Every single row carries the same four-member `unmeasured_columns` list:

```
["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]
```

`unrecognised_columns` and `indeterminate_columns` are empty on all 68, so this is not a parse failure — the columns were simply never written.

The consequence is stated by the extractor itself:

```
context_position_cost:
  total_rows: 68
  measured_rows: 0
  unmeasured_rows: 68
  by_phase: 4-plan 1/0, 5-execute 6/0, 6-finalize 61/0
  position_multiple: unmeasured
  position_multiple_basis: unmeasured
```

Every row records `total_tokens`, `tool_uses` and `duration_ms` correctly — the decomposition alone is absent.

## Root cause

`record-dispatch-boundary` writes the aggregate triple but not the four-way `message.usage` decomposition. The reader (`analyze-logs`, `context_position_cost`) is built to compute a per-position cost multiple from `cache_read_input_tokens ÷ tool_uses` across the boundary rows, and it cannot, on any plan.

This is a producer/consumer gap, not a defect in either half in isolation. It is honest — the extractor publishes `measured_rows: 0` beside `total_rows: 68` and refuses to emit a `position_multiple`, which is exactly the discipline this epic exists to enforce — but the honest zero is a permanent one.

The cost of the gap is specific. `5-execute`'s phase row *does* carry the decomposition (from `enrich`, over the main-context window): `cache_read_input_tokens: 753,983,951`, `cache_read_per_tool_use: 3,886,515`, `billing_weighted_total: 91,806,567`. That single phase row is the only place in this plan where the context-position question can be asked at all, and it covers 194 of the plan's 3148 tool uses. The 61 finalize boundary rows — 2245 tool uses and 11.27M dispatched tokens, the bulk of the plan — carry nothing.

## Proposed action

Have `record-dispatch-boundary` accept and persist the four decomposition columns, defaulting each to the `unmeasured` token when the caller has no `<usage>` envelope (the same three-state discipline `record-step`'s token triple already implements, and which this very plan built). The dispatcher call sites that already parse a `<usage>` tag to obtain `total_tokens` have the four sub-values in hand at that moment.

Until then, `context_position_cost` should keep reporting `unmeasured` — the current behaviour is correct and must not be "fixed" by substituting the aggregate.

## Evidence

- aspect: log_analysis — `context_position_cost.measured_rows: 0` of `total_rows: 68`; every row's `unmeasured_columns` carries all four names
- aspect: logging_gap_analysis — recorded as a `DISPATCH_TERMINATION_CAUSE` gap: "the recorder writes the boundary row without the decomposition the consumer needs"
- aspect: plan_efficiency — `5-execute` is the only phase carrying the decomposition, and it covers 194 of 3148 tool uses
