envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:12Z

# Candidate lesson: deep-lane outline re-entry skipped CERTAIN_INCLUDE assessment recording

**Signal source**: Q-Gate finding 3-outline `6a2b60` (assessment_coverage, warning) and user-review finding `0a8053`. Both were taken_into_account in-run.

**Component (suggested)**: `plan-marshall:phase-3-outline` (deep lane, loop-back re-entry)

## Evidence

- Decision log 2026-10-10T18:51:49Z: q-gate-validation "Starting verification: 5 deliverables, 0 assessments". Every deliverable failed on "no CERTAIN_INCLUDE assessment backs its files".
- The outline had been re-dispatched after an operator `outline_prompt` answer (18:43, adding D5). On that re-entry no assessments were recorded for any of the 73 affected files.
- The operator asked for the finding to be fixed rather than accepted. The re-dispatch then recorded 72 assessments via `manage-findings assessment add` (19:00:04Z), and re-validation reported 73 assessments (19:02:34Z).

## Why it matters

The validator caught the gap. But an outline that skips assessment recording on a re-entry costs a full validation round plus a user review round to restore something the deep lane is meant to produce every time.

## Suggested direction (for orchestrator classification)

Make the deep-lane outline record (or carry forward) a CERTAIN_INCLUDE assessment for every affected file on every pass, re-entries included, or have it assert the coverage before returning.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-010.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
