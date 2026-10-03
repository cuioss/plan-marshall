envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:42:33Z

component=plan-marshall:phase-6-finalize
category=bug

# Write step id and context-load figures on every dispatch-boundary row

## Context

All 15 dispatch-boundary rows of orchestrator-land-verbs (1 in 4-plan, 10 in 5-execute, 4 in 6-finalize) are keyless — no `--step-id` — and carry all four context-load columns as `unmeasured`. The dispatch audit's firing comparison therefore paired 0 of 20 execution-log rows. Finalize wrote only 4 boundary rows although 6 finalize steps were token-proven dispatched and the dispatcher logged 16 finalize dispatch lines, so most finalize spend has no per-dispatch record.

## Root cause

The record-dispatch-boundary call sites omit `--step-id` and the four `--*-tokens` context-load flags, and several finalize dispatches (create-pr, automatic-review firings, later self-review rounds) never call the recorder at all.

## Proposed action

Recurrence of active lesson 2026-10-02-10-008 — merge into it. Extend its scope: every finalize dispatch must record a boundary row, and the call must carry the bare step id plus the normalized context-load figures when the runtime supplies them.

## Evidence

- aspect: execution_context_dispatch_audit — firing_comparison keyless_boundary_rows 1/10/4, paired_firings 0 in every phase
- aspect: log_analysis — context_position_cost measured_rows 0 of 15
- aspect: logging_gap_analysis — 4 finalize boundary rows vs 16 finalize dispatch lines
