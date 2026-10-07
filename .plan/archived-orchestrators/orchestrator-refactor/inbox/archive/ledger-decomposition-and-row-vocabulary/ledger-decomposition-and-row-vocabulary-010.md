envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:05:41Z

# Log STEP and DISPATCH lines for every loop-back re-fire

component: plan-marshall:phase-6-finalize
category: bug

## Context

In ledger-decomposition-and-row-vocabulary, finalize loop-back iteration 1 logged its re-entry ("re-entering finalize step loop from start") and a `[STEP] Executing` line for each re-fired step. Iterations 2 and 3 re-fired lessons-housekeeping, simplify, plugin-doctor and self-review with no `[STEP] Executing` line and no re-entry STATUS line. Iteration 3 also dispatched three of them in parallel. In addition, 5 envelopes completed with no `[DISPATCH]` line: the 4 `self-review-loopback-fix` envelopes, the iteration-2 lessons-housekeeping, and the second branch-cleanup envelope. The dispatch audit rates channel completeness low (11 finalize dispatch lines against 30 step completions, ratio 0.367). Also, all 17 finalize dispatch-boundary rows carry no step_id, so 0 of 30 firings pair with their cost.

## Root cause

The re-entry, step-start and dispatch log lines are emitted by the step loop's first-pass path. The loop-back resume path, and the ad-hoc fix-envelope dispatches, bypass that emitter.

## Proposed action

Route every loop-back re-fire and every loop-back fix dispatch through the same emitter that writes `[STEP] Executing`, the `Loop-back N` re-entry STATUS line, and `[DISPATCH]`. Have `record-dispatch-boundary` carry the step_id so firings pair with their cost.

## Evidence

- aspect: logging_gap_analysis — iterations 2-3 lack STEP/re-entry lines; 5 envelopes lack DISPATCH lines
- aspect: execution_context_dispatch_audit — channel_completeness ratio 0.367, confidence low; firing_comparison 6-finalize 17 keyless boundary rows, 0 paired
