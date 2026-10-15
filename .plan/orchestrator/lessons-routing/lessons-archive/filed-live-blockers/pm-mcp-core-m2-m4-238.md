envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:57Z

# Candidate lesson (Q-Gate finding 1ebb35, 3-outline, accepted): deep-lane outline records no component assessments, so the assessment-coverage validator always fails

**Source plan:** plan-21-entity-addressing
**Signal source:** Q-Gate finding 1ebb35 (phase 3-outline, severity warning, resolution accepted)
**Suggested component:** plan-marshall:phase-3-outline (deep-lane assessment recording) / q-gate validator 2.2

## Finding

`assessment list --certainty CERTAIN_INCLUDE` returned total_count 0 with findings_store_state missing: the deep-lane outline recorded no component assessments, so none of the affected files of deliverables 1-6 (24 write paths plus read references) was backed by an assessment. All six deliverables were flagged "fail - assessment coverage only" although every substantive validator was clean (paths on disk, scope sweeps agree with the declared files).

## Resolution in run

Accepted by the orchestrator as a bookkeeping gap only (q_gate_validation=once, plan_without_asking=true).

## Why it may be lesson-worthy

Either the deep-lane outline in this project skips the assessment step it is expected to perform, or the validator demands an artifact this outline flow does not produce. In both cases the Q-Gate flags every deliverable for a non-substantive reason, which dilutes the gate. Worth checking whether the deep-lane outline should record CERTAIN_INCLUDE assessments for its write paths, or whether validator 2.2 should skip when the outline flow produces none.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-005.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
