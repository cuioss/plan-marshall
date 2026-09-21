envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:26:50Z

component=plan-marshall:manage-metrics
category=improvement
confidence=medium
title=record-dispatch-boundary drops the four token component fields it is asked to analyse

# record-dispatch-boundary drops the four token component fields it is asked to analyse

## Context

`analyze-logs` publishes a `context_position_cost` block whose purpose is to derive
`cache_read_per_tool_use` and a `position_multiple` — how much more a token costs late
in a context window than early. On this plan it reported:

- `total_rows: 103`, `measured_rows: 0`, `unmeasured_rows: 103`
- per phase: 4-plan 0/2, 5-execute 0/10, 6-finalize 0/91
- `position_multiple: unmeasured`, `position_multiple_basis: unmeasured`

Every one of the 103 dispatch-boundary rows carries a populated `total_tokens` and an
`unmeasured_columns` list naming all four components: `input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`.

A 0-of-103 measurement rate across every phase is not a property of this plan. The
analysis is structurally unmeasurable on every plan that uses the current recorder.

## Root cause

`record-dispatch-boundary` captures the aggregate `total_tokens` and does not capture
the four component figures, while the consumer that needs them is already written and
shipping.

## Proposed action

Extend `record-dispatch-boundary` to capture the four component token fields alongside
`total_tokens`, and have the dispatch sites pass them. Then `context_position_cost`
becomes measurable without any consumer change.

Until then the block is behaving correctly and should NOT be changed: it publishes
`measured_rows` against `total_rows` and emits the `unmeasured` sentinel rather than a
fabricated multiple. This lesson is about the producer, not the reporter.

Given `TOKEN REDUCTION IS PRIORITY 1` and that ~99% of billing weight is context rather
than generation, a working position-cost measurement is a direct instrument for that
goal — which is what lifts this above routine instrumentation debt.

## Evidence

- aspect: log_analysis — `context_position_cost` with `measured_rows: 0` of 103, broken down per phase
- aspect: logging_gap_analysis — gap row and `warning` finding on the same figures
- every row's `unmeasured_columns` names the same four fields
