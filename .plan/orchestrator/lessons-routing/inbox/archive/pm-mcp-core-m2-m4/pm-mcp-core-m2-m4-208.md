envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:52Z

# Record dispatch boundaries and DISPATCH lines for every finalize-phase dispatch

## Context

In plan diagram-generator, 6-finalize was the most expensive phase (1.61M of 3.76M tokens, still an unclosed floor) but left the least telemetry. There is no `work/metrics-dispatch-boundaries-6-finalize.toon`, although finalize dispatched create-pr, automatic-review (x2), sonar-roundtrip (x2), unified triage (x2), finalize-rebase-fix, lessons-capture and the retrospective. finalize-rebase-fix, sonar-roundtrip and the loop-back TASK-006 phase-5 re-dispatch each logged a `Complete` line with no `[DISPATCH]` line. The loop-back execute dispatch also recorded no 5-execute boundary row (3 rows for 4 dispatches).

## Root cause

The finalize dispatcher and the loop-back re-entry path do not reach the `[DISPATCH]` emission seam or `record-dispatch-boundary` for every dispatch class. Ad-hoc dispatches such as the rebase fix and sonar-roundtrip miss both.

## Proposed action

Route every finalize dispatch, including ad-hoc repair dispatches and loop-back re-entries into 5-execute, through the same emit-and-record seam. Then the dispatch audit's channel_completeness (0.357 here, confidence low) and the 6-finalize firing comparison (not_evaluated here) become measurable.

## Evidence

- execution-context-dispatch-audit: channel_completeness dispatch_line_count 5 vs completion_count 14, ratio 0.357, confidence low; dispatch_coverage 9/9 no_evidence; firing_comparison 6-finalize not_evaluated (no boundary file)
- logging-gap-analysis: no 6-finalize boundary file; TASK-006 execute dispatch without a boundary row
- log-analysis: dispatch_boundaries has 4-plan and 5-execute only

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-007.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
