envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:08Z

# Candidate lesson: hand-off rows are recorded without a step id and without token breakdown, so the dispatch audit can pair nothing

- Component: plan-marshall:manage-metrics
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-08-005 (created 2026-10-10), epic pm-mcp-core-m2-m4

Source: retrospective of the plan (aspects dispatch audit, log analysis, logging gaps, routing decisions). All figures are script output.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.
Proposed component: `plan-marshall:manage-metrics` (the `record-dispatch-boundary` call sites of the phase dispatchers). Proposed category: improvement.

## Context

The plan recorded 18 hand-off rows (`work/metrics-dispatch-boundaries-{4-plan,5-execute,6-finalize}.toon`: 1, 6 and 11 rows). The retrospective's dispatch audit compares these rows with the per-step execution rows, firing by firing, on the shared step id.

On this plan the comparison paired 0 firings in every phase:

- 4-plan: 1 hand-off row, 1 without step id.
- 5-execute: 6 hand-off rows, 6 without step id; 7 execution rows unpaired.
- 6-finalize: 11 hand-off rows, 11 without step id; 21 execution rows unpaired.

The same 18 rows list `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens` as unmeasured, so the context-position cost is `unmeasured` for all three phases, and the routing check reports 18 of 28 execution rows unmeasured.

## Root cause

The rows are written with the total, the tool-use count, the duration and the cause, but without the step id and without the token breakdown. Both are available to the caller at the moment it records the row: it knows which step it handed off, and the usage block it reads the total from carries the breakdown.

## Consequences seen on this plan

- The audit graded its own evidence `confidence: low` (6 distinct finalize hand-off lines against 17 step completions, ratio 0.353).
- Its clean verdict on logged hand-offs (0 of 26) is marked `uncorroborated`: all 26 hand-off lines came from a caller other than the one whose resolve record they are counted against (`foreign_caller_line_total: 26`).
- Four finalize steps have no token record at all (`branch-cleanup`, `ci-verify`, `pre-push-quality-gate`, `push`), so whether they ran inside the main session or were handed off cannot be told from the record.

None of this is a finding against the run. It means the audit could not check the run.

## Proposed action

Pass the step id and the four token columns when the hand-off row is recorded. Then check whether the caller attribution that produces `foreign_caller_lines` on every role is intended, since it makes every clean verdict uncorroborated.

## Evidence

- aspect execution_context_dispatch_audit: `firing_comparison` with `paired_firings: 0` and `keyless_boundary_rows` 1, 6, 11; `channel_completeness.confidence: low`; `shape_violation.corroboration: uncorroborated`.
- aspect log_analysis: `context_position_cost` with `measured_rows: 0`, `unmeasured_rows: 18`.
- aspect routing_decisions: `execution_log_rows_measured: 10`, `execution_log_rows_unmeasured: 18`.

Classification is left to the pickup.
