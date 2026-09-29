envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=candidate-lesson
created=2026-09-29T13:39:55Z

component=plan-marshall:phase-6-finalize
category=bug

# Forward --step-id on every record-dispatch-boundary call

## Context

In plan-12-tool-triage none of the 99 dispatch-boundary rows carries a `step_id`: 2 in 4-plan, 16 in 5-execute, 81 in 6-finalize. All 99 rows also record the four context-load columns (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) as `unmeasured`. As a result the dispatch audit's `firing_comparison` paired 0 firings against 35 execute and 93 finalize execution-log rows, and `context_position_cost` is unmeasured for the whole plan.

## Root cause

`manage-metrics record-dispatch-boundary` documents `--step-id` as the key-first join (forward it on every call; an omitted flag writes an empty key). The dispatch sites in this run (phase-6-finalize dispatcher, plan-marshall orchestrator) did not forward it, and did not forward the per-dispatch context-load flags either.

## Proposed action

Pass `--step-id {step key}` at every record-dispatch-boundary call site in phase-6-finalize and the plan-marshall orchestrator, plus the four context-load flags whenever the dispatch return carries them. Add a retrospective check that grades a plan whose keyless-row share is 100% as a finding rather than an evaluated pass.

## Evidence

- aspect: execution_context_dispatch_audit — keyless_boundary_rows 2/16/81, paired_firings 0 in every phase
- aspect: log_analysis — context_position_cost measured_rows 0 of 99
- aspect: logging_gap_analysis — DISPATCH_TERMINATION_CAUSE gap
