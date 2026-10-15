envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T13:50:25Z

# Candidate lesson: deep outline lane recorded no CERTAIN_INCLUDE assessments

- Source: Q-Gate finding c48e6a (phase 3-outline, severity warning, resolution accepted)
- Plan: session-log-and-generations (PR #51)
- Signal: signal_qgate_pending_count

## Observation

The deep outline lane produced 7 deliverables with about 70 affected files, yet
`assessment list --certainty CERTAIN_INCLUDE` returned 0 rows (findings store state:
missing). Validator 2.2 therefore flagged every affected file as lacking a backing
assessment. The same Q-Gate pass verified every affected path directly (write-replace
and read paths exist, write-new absent, consumers of the removed seam and of
FORMAT_VERSION enumerated), so the outline itself was sound.

## Resolution in run

Accepted by the orchestrator as a process gap, not an outline defect.

## Possible lesson

Either the deep outline lane should record its CERTAIN_INCLUDE assessments as it
derives the affected-file set, or validator 2.2 should accept the Q-Gate's own direct
path verification as backing evidence instead of raising a finding that is always
accepted. Owning component is likely plan-marshall:phase-3-outline.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `session-log-and-generations-001.md` from plan session-log-and-generations (PLAN-12, #51; Claude Code)
