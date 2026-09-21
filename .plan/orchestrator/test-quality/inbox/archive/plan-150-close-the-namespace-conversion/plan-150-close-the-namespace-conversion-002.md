envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:53:12Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=plan-150-close-the-namespace-conversion

# Pass the four context-load flags at every record-dispatch-boundary call site

## Context

`manage-metrics record-dispatch-boundary` declares four optional per-dispatch context-load
flags — `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens` and
`--cache-creation-input-tokens` — and deliberately writes the literal `unmeasured` into a
column whose flag was omitted, so that "the caller passed no measurement" stays
distinguishable from "the dispatch loaded zero context".

This plan recorded 13 dispatch-boundary rows across three phases (1 in `4-plan`, 4 in
`5-execute`, 8 in `6-finalize`). All 13 carry all four columns as `unmeasured`:
`measured_rows: 0`, `unmeasured_rows: 13`, `position_multiple: unmeasured`,
`position_multiple_basis: unmeasured`.

The instrumentation exists, is correctly designed to distinguish absent from zero, and is
fed by nothing.

## Root cause

No `record-dispatch-boundary` call site in `phase-5-execute` or `phase-6-finalize` forwards
the four values, so the honest-absence path fires on every row. Because the columns are
optional and their absence is a legitimate state, nothing fails and no check reports the
gap — the instrument reports `unmeasured` forever and reads as working.

## Proposed action

Forward the dispatched agent's four-field `message.usage` view at every
`record-dispatch-boundary` call site, in `phase-5-execute` and `phase-6-finalize` alike.
Then consider whether a phase in which every row is `unmeasured` should itself be surfaced —
an all-unmeasured population is the shape that makes an unfed instrument invisible.

## Evidence

- aspect: logging_gap_analysis — gap `all-dispatching-phases / DISPATCH_TERMINATION_CAUSE`: 0 of 13 rows measured
- aspect: log_analysis — `context_position_cost.total_rows: 13`, `measured_rows: 0`, `unmeasured_rows: 13`, `position_multiple: unmeasured`
- aspect: log_analysis — every row in all three `dispatch_boundaries` blocks carries `unmeasured_columns: ["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]`
