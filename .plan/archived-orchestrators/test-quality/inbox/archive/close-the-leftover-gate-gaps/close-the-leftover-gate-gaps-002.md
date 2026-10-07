envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:04:22Z

component=plan-marshall:manage-metrics
category=improvement
title=Record dispatch boundaries for 6-finalize dispatches

# Record dispatch boundaries for 6-finalize dispatches

## Context

In plan close-the-leftover-gate-gaps, work/metrics-dispatch-boundaries-5-execute.toon holds 1 row (clean_exit_queue_empty) but no work/metrics-dispatch-boundaries-6-finalize.toon exists — while the 6-finalize phase carried the majority of dispatch activity (16 terminal steps, 22 DISPATCH lines across callers).

## Root cause

record-dispatch-boundary is called by the execute-phase orchestration path only; the finalize dispatcher records step outcomes via mark-step-done but never stamps the dispatch-termination ledger, so finalize dispatch spend is unaudited by boundary rows.

## Proposed action

Stamp one record-dispatch-boundary row per finalize-step dispatch termination (termination-cause vocabulary already covers step_complete / returned_with_findings), or document the finalize exclusion as a declared subset alongside the existing dispatch_boundary_excluded_classes.

## Evidence

- aspect: logging_gap_analysis — no 6-finalize boundary file, finalize dispatch spend unaudited
- aspect: log_analysis — dispatch_boundaries carries 5-execute only
- aspect: execution-context-dispatch-audit — channel confidence low, 8 finalize-scoped lines vs 23 completions
