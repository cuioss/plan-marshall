envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:57:49Z

component=plan-marshall:plan-marshall
category=bug
confidence=high
source_aspects=logging_gap_analysis,execution_context_dispatch_audit,log_analysis

# Record a dispatch boundary for every phase dispatch, not only early ones

## Context

In lb-33 the dispatch-boundary ledger holds 10 execute rows ending at 2026-10-10T12:24:56Z and 15 finalize rows ending at 09:43:26Z. The session nonetheless ran at least 3 more execute dispatches (TASK-29, TASK-30/31 with the phase transition, TASK-32) and at least 20 more finalize dispatches (housekeeping, plugin-doctor, self-review and verifier rounds, four automatic-review passes, three triage rounds) until about 17:00Z. Every row is also keyless (no step_id), so firing_comparison paired 0 of 38 execution-log rows.

## Root cause

The orchestrator stopped calling `manage-metrics record-dispatch-boundary` after its later dispatches, probably once loop-back rounds and resumes were driven from condensed context, and the call carries no step key, so nothing detects the gap at write time.

## Proposed action

Make the boundary record part of the dispatch seam itself (emit it alongside the [DISPATCH] work-log line, with `--step-id`), or add a phase-exit check that compares boundary rows with dispatch lines and fails loudly when they diverge.

## Evidence

- aspect: logging_gap_analysis — boundary rows stop at 09:43Z (finalize) and 12:25Z (execute) while dispatches continued
- aspect: execution_context_dispatch_audit — channel confidence low (11 finalize dispatch lines vs 47 completions); keyless_boundary_rows 26 of 26, paired_firings 0
- aspect: log_analysis — context_position_cost measured_rows 0 of 26
