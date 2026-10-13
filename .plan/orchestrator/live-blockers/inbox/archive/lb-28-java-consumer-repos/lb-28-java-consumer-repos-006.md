envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T23:28:35Z

component=plan-marshall:plan-marshall
category=improvement
bundle=plan-marshall

# Pass --step-id and context-load flags on every record-dispatch-boundary call

## Context

In plan lb-28-java-consumer-repos all 28 dispatch-boundary rows (1 in 4-plan, 7 in 5-execute, 20 in 6-finalize) were recorded with no `--step-id` and with all four context-load columns `unmeasured`. The retrospective's firing comparison therefore paired 0 boundary rows against 47 execution-log rows (every row keyless, so even the timestamp fallback found nothing), and the context-position cost was unmeasured for the whole plan. The dispatch audit graded its own channel confidence `low`.

## Root cause

The orchestrator call sites invoke `manage-metrics record-dispatch-boundary` with only the cause and the total/tool/duration figures; the step key and the normalized input/output/cache figures are available at the call site but are not forwarded.

## Proposed action

At every `record-dispatch-boundary` call site in the plan-marshall execution/finalize dispatch flow (and phase-6-finalize's per-step dispatcher), forward `--step-id` (the dispatched step key, or the task/envelope key for phase 5) and the four context-load flags whenever the return carries them. Add a check (doctor rule or retrospective finding) that flags a plan whose boundary rows are 100% keyless.

## Evidence

- aspect: execution_context_dispatch_audit — keyless_boundary_rows 1/7/20 of 1/7/20, paired_firings 0 in every phase, channel confidence low
- aspect: log_analysis — context_position_cost measured_rows 0 of 28
- aspect: logging_gap_analysis — DISPATCH_TERMINATION_CAUSE rows carry no step_id
