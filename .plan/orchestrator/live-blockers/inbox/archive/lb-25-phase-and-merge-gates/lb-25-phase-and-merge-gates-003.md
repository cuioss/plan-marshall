envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:12Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Align triage.md fix-task deliverable with what manage-tasks commit-add accepts

## Context

Two separate finalize triage leaves in lb-25-phase-and-merge-gates followed `plan-marshall/workflow/triage.md`, which says fix tasks use `deliverable: 0`. Both times `manage-tasks commit-add` rejected it ("Missing required field: deliverable"), and each leaf improvised by attaching the fix task to an existing deliverable (TASK-21 and TASK-22 to deliverable 10, TASK-23 to deliverable 3).

## Root cause

The documented value and the script's validation disagree: `triage.md` prescribes `deliverable: 0` while `commit-add` treats `0` as missing.

## Proposed action

Decide the contract once: either let `commit-add` accept `deliverable: 0` as the "fix task, no owning deliverable" sentinel, or change `triage.md` to require the owning deliverable number and say how to pick it. Add a test that creates a triage fix task exactly as `triage.md` documents it.

## Evidence

- aspect: chat_history_analysis - triage leaf 1: "The triage doc says fix tasks use deliverable: 0, but commit-add rejected it (Missing required field: deliverable). I used deliverable 10"
- aspect: chat_history_analysis - triage leaf 2: "commit-add rejected deliverable 0, and TASK-21 already set the deliverable-10 precedent"
