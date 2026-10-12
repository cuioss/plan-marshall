envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:33Z

# Candidate lesson: phase-3/phase-4 leaves self-transition the status and leave the metrics boundary half-stamped

Component: plan-marshall:phase-3-outline / plan-marshall:phase-4-plan / plan-marshall:manage-metrics
Category (proposed): bug
Source: plan code-analysis-base, phase transitions 3-outline -> 4-plan -> 5-execute

## Observation

The dispatched phase-3 and phase-4 leaves performed the phase status transition themselves instead of returning to the orchestrator for it. The orchestrator owns the paired metrics stamping (end of the old phase, start of the new one); because the leaf transitioned first, only one side of the boundary was stamped and the phase duration/token record for that boundary is incomplete.

## Proposed correction

Either the leaves must not transition (the phase workflow returns a signal and the orchestrator transitions and stamps both ends), or the transition verb itself stamps both metric boundaries atomically so no caller can produce a half-stamped boundary. A metrics check that flags a phase with a start but no end (or vice versa) would make the defect visible.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-007.md` from plan code-analysis-base (PLAN-36, #31)
