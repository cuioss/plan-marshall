envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:53Z

# Candidate lesson: deep-lane outline written without the assessment pass

- Component: plan-marshall:phase-3-outline
- Suggested category: bug
- Signal: Q-Gate finding 447991 (3-outline, resolution taken_into_account)

## Evidence

- Q-Gate 447991: the assessment store was empty (`findings_store_state: missing`) on a deep-lane plan,
  so none of the affected files of deliverables 1-8 was backed by a CERTAIN_INCLUDE assessment
  (validator 2.2).
- Resolution: the assessment pass was run afterwards and recorded 60 CERTAIN_INCLUDE assessments.

## Suggested correction

The deep lane must not hand the outline to the Q-Gate before the assessment pass has written its
records. Assert this before the gate, not in the gate.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-012.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
