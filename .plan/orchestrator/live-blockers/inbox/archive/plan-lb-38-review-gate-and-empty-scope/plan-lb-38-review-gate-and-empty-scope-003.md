envelope_version=1
sender_type=plan
sender_id=plan-lb-38-review-gate-and-empty-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T23:06:14Z

component=plan-marshall:plan-marshall
category=bug

# Forward --step-id on every record-dispatch-boundary call so ledgers join on key

## Context

In plan-lb-38 all 16 dispatch-boundary rows (4-plan 1, 5-execute 6, 6-finalize 9) were written with an empty step_id. The retrospective's firing comparison therefore paired 0 firings in every phase, leaving 16 execute and 22 finalize execution_log rows unpaired, and reconcile-ledgers falls back to timestamp windows for the whole plan.

## Root cause

The orchestrator call sites invoke manage-metrics record-dispatch-boundary without --step-id, although the verb's contract says to forward the dispatch's step key on every call and that an omitted flag is correct only when the dispatch genuinely has no step.

## Proposed action

Pass --step-id {step key} at every record-dispatch-boundary call site in the plan-marshall execution and finalize workflows (phase-5 envelope dispatches and phase-6 step dispatches), and add a retrospective or plan-doctor check that reports keyless boundary rows on a phase that has execution_log rows.

## Evidence

- aspect: execution_context_dispatch_audit - firing_comparison keyless_boundary_rows 1/6/9 of 1/6/9, paired_firings 0 in all three phases
- aspect: logging_gap_analysis - DISPATCH_TERMINATION_CAUSE gap: no boundary row carries a step_id
- aspect: log_analysis - context_position_cost unmeasured on all 16 rows (context-load columns also omitted)
