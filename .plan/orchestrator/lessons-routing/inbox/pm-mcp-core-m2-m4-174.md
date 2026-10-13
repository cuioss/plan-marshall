envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:12Z

# Candidate (Q-Gate 3-outline, accepted): assessment_coverage fires on a deep-lane outline that records no assessments

Source: Q-Gate finding 0feabd, phase 3-outline, warning; resolution accepted.

## Finding

`assessment list --certainty CERTAIN_INCLUDE` returned 0 records (findings_store_state: missing) for this deep-lane plan, so none of the affected files of deliverables 1-8 was backed by an assessment.

## Resolution

The operator accepted it: this domain's outline flow records no assessments, so the check does not apply here.

## Lesson shape

The gate fires on every deep-lane plan in a domain whose outline flow writes no assessments, and each time it costs an operator acceptance. Either the outline flow should record CERTAIN_INCLUDE assessments, or the gate should check whether the domain produces assessments before raising the finding.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-008.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
