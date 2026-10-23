envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:50Z

component=plan-marshall:plan-marshall
category=bug
created=2026-10-18

# Pass --step-id on every record-dispatch-boundary call

## Context

All 46 dispatch-boundary rows of plan-20-job-runner (1 in 4-plan, 8 in 5-execute, 37 in 6-finalize) carry no step_id. The retrospective's firing comparison therefore paired 0 boundary rows against 52 execution_log rows, and every row was reported keyless. All 46 rows also record the four context-load columns as `unmeasured`, so the per-dispatch context-position cost could not be computed.

## Root cause

The orchestrator-side callers of `manage-metrics record-dispatch-boundary` omit `--step-id` (and the context-load flags), although the SKILL says to forward the dispatch's step key on every call.

## Proposed action

Make the phase-5 and phase-6 dispatch sites pass `--step-id` (the same key `record-step` writes) and the normalized `{input, output, cache_read, cache_creation}` figures when the runtime returns them. Consider making `--step-id` required for the `step_complete` and `returned_with_findings` causes so an omission fails loudly.

## Evidence

- aspect: execution-context-dispatch-audit - firing_comparison: 5-execute keyless_boundary_rows 8, 6-finalize keyless_boundary_rows 37, paired_firings 0
- aspect: log-analysis - context_position_cost: unmeasured_rows 46 of 46
- aspect: logging_gap_analysis - DISPATCH_STEP_KEY 0 of 46
