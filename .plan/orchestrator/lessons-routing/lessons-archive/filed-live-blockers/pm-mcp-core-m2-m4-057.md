envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:42Z

Candidate lesson (source: Q-Gate finding 8a5fb0, phase 3-outline, plan http-baseline).

The deep outline lane finished with an empty assessment store: no CERTAIN_INCLUDE assessment was recorded for any of the 12 affected files of deliverables 1-4, so the Q-Gate assessment-coverage check (2.2) raised a finding. The file set itself was correct (a complete content sweep over 302 files corroborated it), and the operator accepted the finding as bookkeeping only.

Observation: the deep lane can produce a correct outline while skipping the assessment write step, and the gap only surfaces at Q-Gate, costing an operator decision. Either the deep lane should write the assessments it already has the evidence for, or the Q-Gate check should accept a recorded complete content sweep as equivalent evidence.

Component candidates: plan-marshall:phase-3-outline (deep lane), plan-marshall:manage-findings (assessment store / Q-Gate check).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-001.md` from plan http-baseline (PLAN-05, #28)
