envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T16:19:56Z

component=plan-marshall:plan-marshall
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Forward the step id on every record-dispatch-boundary call

# Forward the step id on every record-dispatch-boundary call


## Context

All 16 dispatch-boundary rows of plan-v2-25 (1 in 4-plan, 6 in 5-execute, 9 in 6-finalize) were recorded without `--step-id`. The dispatch audit's `firing_comparison` therefore paired 0 boundary rows with the 22 `execution_log` rows (`keyless_boundary_rows` equals `boundary_rows` in every phase), and per-dispatch context-load columns were all `unmeasured`.

## Root cause

The orchestrator's `record-dispatch-boundary` call sites omit `--step-id` (and the four context-load flags), although manage-metrics documents that the key must be forwarded on every call that has a step.

## Proposed action

Pass the dispatched step key (`record-step` step_id, e.g. `automatic-review`, `verify:module-tests`) on every `record-dispatch-boundary` call in the phase-5 and phase-6 dispatch paths, and forward the context-load figures where the return carries them.

## Evidence

- aspect: execution_context_dispatch_audit — firing_comparison paired_firings 0 in 4-plan, 5-execute and 6-finalize; channel confidence low
- aspect: logging_gap_analysis — DISPATCH_TERMINATION_CAUSE gap, 16 of 16 rows keyless
- aspect: log_analysis — context_position_cost measured_rows 0 of 16
