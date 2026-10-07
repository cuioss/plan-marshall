envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=candidate-lesson
created=2026-09-28T16:11:01Z

# Forward step_id and emit DISPATCH on every finalize and execute dispatch record

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_aspects: execution_context_dispatch_audit, logging_gap_analysis

## Context

In plan-13-finalize-mechanism-defects, 25 of 30 `6-finalize` dispatch-boundary rows and 8 of 9
`5-execute` rows were recorded without `--step-id`, so `check-dispatch-audit`'s
`firing_comparison` paired only 3 of 30 finalize dispatches with their `record-step` rows and
fell back to timestamp windows for the rest. Separately, 7 finalize steps carry token proof of a
dispatched envelope but only 4 distinct finalize-dispatcher `[DISPATCH]` lines exist, so
`missing_dispatch_emission` is 3 (a floor) and the dispatch channel is graded `confidence: low`.

## Root cause

Both audit channels depend on the orchestrator hand-issuing the recording calls with the right
identity after each return: `record-dispatch-boundary --step-id` is documented as "forward on
EVERY call" but is optional at argparse, and the `[DISPATCH]` line is only emitted when the
resolve call carries `--workflow`. Neither omission fails anything, so the audit degrades
silently over a long finalize with many re-fires.

## Proposed action

1. In the `phase-6-finalize` dispatcher (item 5 post-return block) and `plan-marshall/workflow/execution.md`,
   make `--step-id {step_id}` part of the literal `record-dispatch-boundary` invocation, not prose.
2. Make the dispatch-boundary recorder warn (or refuse) when `--step-id` is absent for a phase
   whose dispatches always have a step key (`6-finalize`).
3. Check that every finalize dispatch site resolves with `--workflow` so the seam emits
   `[DISPATCH]` itself; add a test that the count of dispatched finalize steps equals the count
   of finalize-dispatcher `[DISPATCH]` lines on a fixture run.

## Evidence

- aspect: execution_context_dispatch_audit — `firing_comparison` 6-finalize: `boundary_rows: 30`, `keyless_boundary_rows: 25`, `paired_firings: 3`; `missing_dispatch_emission: 3`, `channel_completeness.confidence: low`
- aspect: logging_gap_analysis — 5-execute `keyless_boundary_rows: 8` of 9
