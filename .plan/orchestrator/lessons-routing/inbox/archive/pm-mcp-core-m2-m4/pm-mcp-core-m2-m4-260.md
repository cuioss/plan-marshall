envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T20:35:31Z

# Candidate lesson: Stamp step_id on dispatch-boundary rows so firings can be paired

**Component (suggested):** plan-marshall:manage-metrics
**Category (suggested):** improvement

## Context

In plan-17-project-units-and-invariants all 11 dispatch-boundary rows (1 in 4-plan, 8 in 5-execute, 2 in
6-finalize) carry no `step_id`. The retrospective's firing comparison therefore paired 0 of the 15
`execution_log` rows in 5-execute and 6-finalize. The finalize phase spent 3,125,209 tokens (38% of the
plan) across 6 automatic-review, 9 sonar-roundtrip and 7 pre-push-quality-gate firings, yet its 2 boundary
rows cover only 277,647 of them, so the spend cannot be split by step or by termination cause.

## Root cause

`manage-metrics record-dispatch-boundary` writes rows without the step key that the execution log uses, and
most finalize dispatch classes record no boundary at all.

## Proposed action

Add a `--step-id` to `record-dispatch-boundary`, have every dispatch site pass the step it dispatched, and
extend boundary recording to the finalize step dispatches (automatic-review, sonar-roundtrip, triage).

## Evidence

- aspect: execution_context_dispatch_audit: firing_comparison keyless_boundary_rows 1 / 8 / 2, paired_firings 0 in every phase; channel_completeness confidence low (6 of 37)
- aspect: logging_gap_analysis: 6-finalize boundary rows cover 277,647 of 3,125,209 tokens
- aspect: log_analysis: dispatch_boundaries 4-plan 1 row, 5-execute 8 rows, 6-finalize 2 rows

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-17-project-units-and-invariants-009.md` from plan plan-17-project-units-and-invariants (PLAN-17, #56; harness Claude Code)
