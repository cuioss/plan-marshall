envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:58:15Z

component=plan-marshall:plan-marshall
category=bug

# Align triage fix-task deliverable 0 with manage-tasks commit-add

## Context

During the unified triage of PR #1742 the triage allocated a fix task as `triage.md` § 3c Shape 1 prescribes, with `deliverable: 0`. `manage-tasks commit-add` rejected it with `Missing required field: deliverable`. The leaf retried with `deliverable: 10` and succeeded, so TASK-23 (and later TASK-24 and TASK-25) were filed under an outline deliverable they do not belong to. A related consequence surfaced in execute: the change ledger stores only `deliverable_id`, and fix-task commits recorded as deliverable 0 could not be looked up by task.

## Root cause

`commit-add` treats the integer 0 as an absent value, while the triage contract uses 0 as the reserved "fix task, no outline deliverable" marker.

## Proposed action

Make `commit-add` accept deliverable 0 explicitly (presence check, not truthiness) or change the triage contract to a named sentinel both sides validate. Add a contract test that allocates a fix task exactly as `triage.md` documents.

## Evidence

- unified triage hand-back (2026-10-09T23:54Z): commit-add rejected deliverable 0, retried with 10
- TASK-23, TASK-24 and TASK-25 all carry deliverable 10
- execute hand-back before TASK-22: change ledger has no task_id, fix-task commits recorded as deliverable 0
