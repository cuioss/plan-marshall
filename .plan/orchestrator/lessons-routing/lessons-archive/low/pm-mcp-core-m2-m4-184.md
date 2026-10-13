envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:18Z

# Candidate lesson: record a dispatch boundary with step_id for every execute and finalize dispatch

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:manage-metrics` (record-dispatch-boundary and its call sites). Category: improvement. Confidence: high.

## Context

The plan dispatched about 6 execute envelopes (envelopes 1 to 3, plus the TASK-17, TASK-18 and TASK-19 loop-back runs) and fired each finalize review-loop step 5 times. Only 2 execute rows and 4 finalize rows were recorded. None of the 7 rows carries a `step_id`, and all four token columns are unmeasured. As a result `firing_comparison` paired 0 rows, the dispatch-audit channel confidence is low (6 finalize dispatch lines for 25 completions), and `context_position_cost` is unmeasured.

## Root cause

Execute loop-back re-dispatches and most finalize dispatches do not call `record-dispatch-boundary`, and the rows that are written carry no shared key with `execution_log[]`.

## Proposed action

Call `record-dispatch-boundary` at every execute and finalize dispatch site, stamp the row with `step_id` (or `envelope_id`/`task_number` for execute), and capture the usage columns when the hand-back carries them.

## Evidence

- aspect: execution-context-dispatch-audit — channel confidence low, 9 of 9 finalize steps no_evidence, 0 paired firings, keyless boundary rows 1/2/4
- aspect: log-analysis — dispatch_boundaries 4-plan 1 row, 5-execute 2 rows, 6-finalize 4 rows; context_position_cost 0 of 7 measured
- aspect: logging-gap-analysis — DISPATCH_TERMINATION_CAUSE coverage gap

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-019.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
