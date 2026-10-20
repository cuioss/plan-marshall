envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:09Z

component=plan-marshall:manage-metrics
category=bug

# Record step_id and token split on every dispatch-boundary row, finalize included

Source: plan-retrospective of plan-70-plan-instance-alignment (aspects log-analysis, execution-context-dispatch-audit, logging-gap-analysis, plan-efficiency).

## Context

All 21 dispatch-boundary rows (4-plan 2, 5-execute 7, 6-finalize 12) are keyless and carry `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens` as unmeasured. The dispatch audit therefore paired 0 of 18 finalize execution rows (`firing_comparison` keyless_boundary_rows 12) and `context_position_cost` measured 0 of 21 rows. 6-finalize also recorded only 12 boundary rows for at least 30 dispatches (4 security audits, 6 functional reviews plus verifiers, 4 code reviews plus verifiers, sonar, review and 3 triage leaves), so its 4.3M token floor understates the phase; 9 of 14 finalize steps have no dispatch evidence at all.

## Root cause

The finalize dispatcher calls `record-dispatch-boundary` without `--step-id` and without the token split, and several finalize dispatch classes (verifiers, triage) do not call it.

## Proposed action

Pass `--step-id` and the four token columns from the `<usage>` tag on every `record-dispatch-boundary` call, and call it for every finalize dispatch including verifier and triage leaves, so the boundary population matches the dispatched population.

## Evidence

- log-analysis: context_position_cost measured_rows 0, unmeasured_rows 21
- execution-context-dispatch-audit: firing_comparison 6-finalize paired_firings 0, unpaired_execution 18; channel_completeness confidence low (ratio 0.242)
- plan-efficiency: 6-finalize 4,300,982 is a boundary floor of an unclosed phase
