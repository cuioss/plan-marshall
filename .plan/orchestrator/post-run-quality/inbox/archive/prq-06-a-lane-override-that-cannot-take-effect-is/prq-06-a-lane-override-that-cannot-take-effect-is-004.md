envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:28Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=log_analysis,logging_gap_analysis,plan_efficiency

# Every dispatch-boundary row records total_tokens and nothing else

## Context

`analyze-logs` reports the plan's `context_position_cost` block as:

```
total_rows: 33
measured_rows: 0
unmeasured_rows: 33
by_phase: 4-plan 1/0, 5-execute 7/0, 6-finalize 25/0
position_multiple: unmeasured
position_multiple_basis: unmeasured
```

Every one of the 33 dispatch-boundary rows across all three dispatching phases lists the same four fields under `unmeasured_columns`:

```
["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]
```

Only `total_tokens` survives. `unrecognised_columns` and `indeterminate_columns` are empty on every row, so this is not a parse failure — the values were never captured.

## Root cause

`record-dispatch-boundary` is being called with the aggregate token figure only; the per-component split from the dispatch's `<usage>` record is not forwarded. The result is a metrics store that can say how many tokens a dispatch cost but not what kind they were.

That matters more than it sounds. Cache reads dominate billing weight by a wide margin, so the plan's largest cost component is the one recorded by nothing, while `metrics.md` still prints a confident `8,444,415` total and the report renders a per-phase breakdown that looks fully measured. A reader cannot tell "this plan was cache-efficient" from "this plan re-read its context 40 times" — which is precisely the question a 50%-of-budget finalize phase raises.

## Proposed action

Forward the four components at the recording call site so `record-dispatch-boundary` stores `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens` beside `total_tokens`. Where a caller genuinely cannot obtain them, it must keep writing them as unmeasured — the column vocabulary already exists and is doing its job here; what is missing is any caller that populates it.

Add a guard: when `measured_rows == 0` over a non-empty `total_rows`, the metrics report should state that the position-cost dimension was not measured at all rather than rendering `position_multiple: unmeasured` as one more quiet field.

## Evidence

- aspect: log_analysis — `context_position_cost: total_rows 33, measured_rows 0, unmeasured_rows 33`
- every `dispatch_boundaries` row in `4-plan`, `5-execute` and `6-finalize` carries the identical four-element `unmeasured_columns` list
- aspect: plan_efficiency — the plan's headline 8.44M total is reported with no component attribution behind it
- aspect: logging_gap_analysis — `CONTEXT_POSITION_COST` gap recorded at `all-phases`
