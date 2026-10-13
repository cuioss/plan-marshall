envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:27Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Record a dispatch boundary with step_id for every finalize dispatch

## Context

In lb-25-phase-and-merge-gates the 6-finalize dispatch-boundary ledger holds 6 rows, the last at 08:35:33Z, while finalize kept dispatching until about 15:54Z (pre-submission-self-review fired 9 times, plugin-doctor 7, automatic-review 3, plus triage and fix leaves). The boundary rows cover 1.6M of the 8.08M tokens the finalize accumulator holds. No boundary row in any phase carries a `step_id` (4-plan 1/1, 5-execute 10/10, 6-finalize 6/6 keyless), so the dispatch audit paired 0 firings against 52 execution-log rows, and its channel confidence is low (8 finalize [DISPATCH] lines against 37 step completions).

## Root cause

The orchestrator calls `accumulate-agent-usage` after finalize returns but does not call `record-dispatch-boundary` on loop-back re-fires and wait-region triage dispatches, and it never forwards `--step-id` on the calls it does make.

## Proposed action

Call `record-dispatch-boundary` after every finalize dispatch return (including re-fires, verifier and author rounds, and triage leaves), always with `--step-id`, and emit the matching [DISPATCH] work-log line. Add a reconcile check that boundary rows and accumulator samples agree per phase.

## Evidence

- aspect: logging_gap_analysis - "6-finalize dispatch-boundary ledger stops at 08:35Z although finalize dispatched for ~7 more hours"
- aspect: execution_context_dispatch_audit - keyless_boundary_rows equal boundary_rows in every phase; paired_firings 0; channel_completeness confidence low (ratio 0.216)
