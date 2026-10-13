envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:18Z

# Candidate lesson: align triage fix-task deliverable 0 with commit-add validation

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:phase-6-finalize` (triage workflow) / `plan-marshall:manage-tasks`. Category: bug. Confidence: high.

## Context

Both finalize triage runs that created fix tasks (TASK-15/16, then TASK-17) hit the same problem. `triage.md` tells them to create the fix task with `deliverable: 0`, and `manage-tasks commit-add` rejected that as "Missing required field". Each leaf picked an existing deliverable (3 or 4) instead, so the fix tasks are filed under deliverables they do not belong to.

## Root cause

The workflow doc and the script validation disagree on whether 0 is a valid deliverable number for fix tasks that no deliverable owns.

## Proposed action

Either accept `deliverable: 0` (or an explicit `origin: finalize-feedback` with no deliverable) in `commit-add`, or change `triage.md` to name the rule for choosing the deliverable. Add a test that the documented fix-task payload passes `commit-add`.

## Evidence

- aspect: chat-history-analysis — triage leaf: "`commit-add` rejected `deliverable: 0` (Missing required field), so I used 4 for TASK-15 and 3 for TASK-16"; second triage leaf: same rejection, used deliverable 4 for TASK-17

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-018.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
