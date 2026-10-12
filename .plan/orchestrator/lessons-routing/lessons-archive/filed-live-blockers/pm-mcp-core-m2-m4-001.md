envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:51Z

# Candidate lesson: Outline quality check reports "no assessment backs any file" when the outline ran no assessment pass

- Component: plan-marshall:phase-3-outline
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-001 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Quality-check finding 9768ef (phase 3-outline, severity warning) of plan primitive-spi-and-validators, resolved `accepted` by the operator on 2026-10-09.

## What happened

The assessment store of the plan held 0 assessments (`findings_store_state: missing`). The assessment-coverage check therefore reported that none of the 34 write paths and 4 read paths of deliverables 1 to 6 is backed by a CERTAIN_INCLUDE assessment. The check could not confirm any file; it did not show that a file is wrongly in scope. File existence was verified separately and passed.

The operator had to settle a finding that states "the check could not run", not a defect of the outline.

The stored finding detail also carried a wrong number: it says 26 of the write paths are new files; the operator's resolution text corrects this to 21.

## Proposed rule

When the outline was written without an assessment pass, the coverage check has nothing to compare against. It should say "not run, no assessments recorded" as its own outcome instead of filing a per-plan warning the operator must accept, or the outline should record assessments for the existing files it changes or reads.

## Evidence

- Finding 9768ef, resolution detail of 2026-10-09T21:46:01Z.
- Decision log dcd63f: "Starting verification: 6 deliverables, 0 assessments".
- Decision log b511a7: operator accepted 9768ef (no assessment pass at outline).


## Recurrence: plan workspace-confinement (PLAN-03 of epic pm-mcp-core-m2-m4), inbox message workspace-confinement-001.md

**Candidate: outline reported its quality check as passed with an empty assessment store (deliverable 1)**

Source record: quality-check finding `264bb2`, phase `3-outline`, source `qgate`, resolved `taken_into_account` in-run.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

## What the record says

The assessment coverage check (2.2) found the plan's assessment store empty (0 `CERTAIN_INCLUDE` assessments, store state `missing`), so none of the 7 affected files of deliverable 1 was backed by an assessment. Every other check passed for those files.

Resolution: a `CERTAIN_INCLUDE` assessment was recorded for each of the 7 files; the two existing files were read on disk, the five write-new files were absent as declared.

## Log evidence

- Work log `c974eb` (21:33:15Z): the outline phase closed with "3 deliverables, Q-Gate: pass".
- Decision log `0d62e9` (21:34:17Z): the validator started with "3 deliverables, 0 assessments".
- Decision log `dcd103`: deliverable 1 flagged only by assessment coverage, 0 of 7 files assessed.
- Decision log `46c126`: validator summary "0 passed, 3 flagged".

## Why it may be a lesson

The outline phase wrote no assessment at all in two dispatches and still reported its own check as passed; the gap surfaced only in the separate validation hand-off and cost one further outline dispatch. Findings `8aa192` and `725bd2` are the same gap for deliverables 2 and 3 and are sent as their own messages.

Classification is left to the pickup.


## Recurrence: plan workspace-confinement (PLAN-03 of epic pm-mcp-core-m2-m4), inbox message workspace-confinement-002.md

**Candidate: no assessments recorded for the write-new files of deliverable 2**

Source record: quality-check finding `8aa192`, phase `3-outline`, source `qgate`, resolved `taken_into_account` in-run.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

## What the record says

The assessment coverage check (2.2) found 0 `CERTAIN_INCLUDE` assessments, so none of the 3 affected files of deliverable 2 (`package-info.java`, `WorkspaceConfinement.java`, `WorkspaceConfinementTest.java` in `de.planmarshall.runtime.workspace` of `pm-runtime`) was backed by an assessment. Paths and write-new intents were verified on disk; the package did not exist yet.

Resolution: a `CERTAIN_INCLUDE` assessment was recorded for each of the 3 write-new files.

## Log evidence

- Decision log `b66270`: deliverable 2 flagged by assessment coverage (0 of 3 files) and by an open design choice (finding `8605b5`, sent separately).

## Why it may be a lesson

Same gap as finding `264bb2` (deliverable 1) and `725bd2` (deliverable 3): the outline recorded no assessment for any affected file. All three files here are write-new, so the record also shows that the coverage check expects an assessment for a file that does not exist yet.

Classification is left to the pickup.


## Recurrence: plan workspace-confinement (PLAN-03 of epic pm-mcp-core-m2-m4), inbox message workspace-confinement-003.md

**Candidate: no assessment recorded for doc/plans/README.adoc (deliverable 3)**

Source record: quality-check finding `725bd2`, phase `3-outline`, source `qgate`, resolved `taken_into_account` in-run, file `doc/plans/README.adoc`.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

## What the record says

The assessment coverage check (2.2) found 0 `CERTAIN_INCLUDE` assessments, so the one affected file of deliverable 3, `doc/plans/README.adoc`, was not backed by an assessment. The file existed and its row `workspace-confinement` read `open`, as the deliverable stated.

Resolution: an assessment was recorded for `doc/plans/README.adoc`, read on disk; the same record covers the file in the later deliverable 4, and `CLAUDE.md` of deliverable 4 got its own assessment.

## Log evidence

- Decision log `79e4f9`: deliverable 3 flagged by assessment coverage (0 of 1 file) and by a sequencing contradiction (finding `df435a`, sent separately).

## Why it may be a lesson

Third instance of the same gap as findings `264bb2` and `8aa192`: the outline recorded no assessment for any affected file, for documentation files as well as for source files.

Classification is left to the pickup.
