envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:17Z

# Candidate lesson: Record a dispatch boundary for every finalize dispatch and do not stamp a productive run as error

- Component: plan-marshall:phase-6-finalize
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-14-015 (created 2026-10-10), epic pm-mcp-core-m2-m4

- component: plan-marshall:phase-6-finalize
- category: improvement
- confidence: high
- source plan: lock-manager-and-leases

## Context

6-finalize recorded only 3 dispatch-boundary rows for at least 9 finalize dispatches (create-pr, three sonar-roundtrip and three automatic-review rounds, unified triage). The dispatch audit rated channel confidence low and found no token evidence for 5 of 8 terminal steps, so finalize spend (873K tokens) cannot be attributed per step. In 5-execute, the 06:39 dispatch that completed TASK-015 was stamped `termination_cause=error` (241K tokens) only because the scope-creep finding could not be persisted, so the error-waste figure counts productive work.

## Root cause

Boundary recording is not issued on every finalize dispatch path (re-fires and concurrent FIND producers miss it), and the termination cause is taken from the return status rather than from whether the work completed.

## Proposed action

Call record-dispatch-boundary on every finalize dispatch, including re-fires after a loop-back, and map a return whose tasks completed but whose post-step failed to a non-error cause (or add one), so error_total_tokens means genuinely wasted spend.

## Evidence

- aspect: execution_context_dispatch_audit — channel confidence low, ratio 0.353, 5 of 8 steps no_evidence
- aspect: log_analysis — dispatch_boundaries 6-finalize rows 3; 5-execute error_total_tokens 240983
- aspect: logging_gap_analysis — finalize boundary coverage gap and error misclassification

Source: inbox `lock-manager-and-leases-019.md`, plan lock-manager-and-leases (PLAN-01, #20).
