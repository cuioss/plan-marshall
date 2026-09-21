envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:40Z

# context_position_cost measured 0 of 98 dispatch rows and cannot produce a position multiple

component: plan-marshall:manage-metrics
category: improvement
confidence: medium

## Context

The `context_position_cost` block of the log-analysis fragment reports, for this plan:

- `total_rows: 98`
- `measured_rows: 0`
- `unmeasured_rows: 98`
- `no_tool_use_rows: 0`
- `position_multiple: unmeasured`
- `position_multiple_basis: unmeasured`
- per phase: `4-plan` 1/0 measured, `5-execute` 20/0 measured, `6-finalize` 77/0 measured — `cache_read_per_tool_use: unmeasured` on all three

Every one of the 98 dispatch-boundary rows lists the same four columns as unmeasured: `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`. Only the aggregate `total_tokens` is present, and on 41 of the 77 finalize rows even that is zero.

## Root cause

The recorder captures an aggregate `total_tokens` per dispatch but not the four component columns the position-cost instrument divides by. This is not a data-loss event like the finalize zeroing — it is uniform across all three dispatching phases and across the whole plan, so the columns were never populated rather than populated and lost.

The instrument's behaviour is correct: it publishes `unmeasured` for both the multiple and its basis rather than emitting a ratio over absent inputs, and it publishes `measured_rows` beside `total_rows` so the coverage is legible. This proposal is not about the reporting — it is that a lever the token roadmap treats as primary produced no observation at all on a 14.4-million-token plan.

## Proposed action

Populate the four component token columns at `record-dispatch-boundary` time from the same `<usage>` source the aggregate already comes from, so `cache_read_per_tool_use` becomes computable. If the source genuinely does not expose the breakdown on the current target, record that fact once as a target capability rather than leaving 98 rows individually unmeasured — a per-row absence and a platform-wide absence need different remedies and currently read identically.

Until then, no change to the reporting is needed: `position_multiple: unmeasured` is the right output for the inputs available.

## Evidence

- aspect: log_analysis — `context_position_cost: measured_rows 0 of total_rows 98`
- aspect: log_analysis — `by_phase` shows `cache_read_per_tool_use: unmeasured` for 4-plan, 5-execute and 6-finalize alike
- aspect: log_analysis — every `dispatch_boundaries` row carries the same four-member `unmeasured_columns` list and an empty `unrecognised_columns`
- scale: the plan reports `totals_tokens: 14414932`, so the absent measurement is not for want of spend to measure
