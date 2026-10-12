envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:13Z

# Outline Q-Gate flags empty assessments on a lane that produces none

## What happened

The outline Q-Gate raised "assessment coverage - no CERTAIN_INCLUDE assessments for any affected
file" (validator 2.2): the assessment store of the plan was empty (`findings_store_state: missing`),
so none of the affected files of deliverables 1 to 13 was backed by an assessment. The outline lane
used for this plan produces no per-file assessments by design. The finding could only be closed by
an operator decision ("accepted: this outline lane produces no per-file assessments"), which cost a
round trip and adds noise to the Q-Gate count that drives lessons-capture.

## Rule

The assessment-coverage check should only apply to outline lanes that are expected to produce
assessments. On a lane that produces none, the validator should either skip the check or report it
as not applicable, rather than raise a pending finding the operator has to accept by hand.

## Evidence to check before acting

Confirm which lane this plan ran (light vs deep) and whether that lane's contract states it writes
no assessments; if the lane is supposed to write them, the defect is the lane, not the validator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-06-store-substrate-003.md` from plan plan-06-store-substrate (PLAN-06, #26)
