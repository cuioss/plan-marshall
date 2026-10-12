envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:45Z

component=plan-marshall:phase-6-finalize
category=bug
title=Record dispatch boundaries for loop-back execute and every finalize dispatch

# Record dispatch boundaries for loop-back execute and every finalize dispatch

## Context

In plan http-baseline the dispatch-boundary files under-cover the dispatches that actually ran. `metrics-dispatch-boundaries-5-execute.toon` holds 5 rows, the last at 07:53Z, although phase-5-execute was re-entered twice more after finalize loop-backs (TASK-9 and TASK-10, after 08:23Z). `metrics-dispatch-boundaries-6-finalize.toon` holds 4 rows against 7 finalize dispatch lines in the work log, and only one `returned_with_findings` row although the session shows three finalize loop-backs to 5-execute. The dispatch audit rated channel confidence `low` (ratio 0.412), and every boundary row is keyless, so firing comparison paired 0 rows in every phase.

## Root cause

The `record-dispatch-boundary` call is not made on the loop-back re-entry path of execute nor for every review-shaped finalize dispatch, and the rows carry no step key to pair them with `execution_log[]`.

## Proposed action

Call `manage-metrics record-dispatch-boundary` on every execute re-entry (including loop-back re-entries from finalize) and after every finalize step dispatch, stamping `returned_with_findings` for loop-back returns, and record the step id on each row so the firing comparison can pair it.

## Evidence

- aspect: logging_gap_analysis - 5-execute boundary rows end at 07:53Z; 6-finalize 4 rows vs 7 dispatch lines, 1 returned_with_findings vs 3 loop-backs
- aspect: execution_context_dispatch_audit - channel_completeness confidence low (7 finalize dispatch lines / 17 completions); firing_comparison keyless_boundary_rows 1/5/4, paired_firings 0
- aspect: chat_history_analysis - three `status: loop_back` finalize hand-backs with loop_back_target 5-execute

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-009.md` from plan http-baseline (PLAN-05, #28)
