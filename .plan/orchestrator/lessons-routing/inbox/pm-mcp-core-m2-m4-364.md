envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:51Z

# Pass --step-id on every finalize record-dispatch-boundary call

- Source: plan-retrospective (execution-context-dispatch-audit, logging-gap-analysis)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:phase-6-finalize
- Category: improvement
- Confidence: high

## Context

All 21 dispatch-boundary rows recorded in 6-finalize are keyless: none carries a step_id. The retrospective's firing comparison therefore paired 0 of 36 execution-log rows (all 36 unpaired, 21 keyless boundary rows). The 4-plan row and the 3 5-execute rows are keyless as well. The finalize [DISPATCH] channel also graded confidence low (9 dispatch lines against 23 completions).

## Root cause

The finalize dispatcher calls `manage-metrics record-dispatch-boundary` without `--step-id`, so the reconciliation between the boundary ledger and `execution_log[]` falls back to a timestamp window and pairs nothing.

## Proposed action

Forward the dispatched step key as `--step-id` on every `record-dispatch-boundary` call in the phase-6-finalize dispatch loop (and in the 4-plan / 5-execute call sites), as the manage-metrics contract already asks.

## Evidence

- aspect: execution-context-dispatch-audit -- firing_comparison 6-finalize: boundary_rows 21, execution_rows 36, paired_firings 0, keyless_boundary_rows 21
- aspect: logging-gap-analysis -- channel_completeness ratio 0.391, confidence low
