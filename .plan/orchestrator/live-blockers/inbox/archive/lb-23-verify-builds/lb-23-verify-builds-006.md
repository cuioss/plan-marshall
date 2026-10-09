envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:53Z

component=plan-marshall:plan-marshall
category=bug
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Align triage fix-task deliverable 0 with the manage-tasks validator

## Context

On plan lb-23-verify-builds four separate triage dispatches (the ones that created TASK-17, TASK-18, TASK-19 and TASK-20 to 23) each followed `plan-marshall/workflow/triage.md`, which prescribes `deliverable: 0` for a fix task, and each had `manage-tasks commit-add` reject it with "Missing required field: deliverable". Each leaf then picked a deliverable by its own judgement (the one that introduced the failing test, the one the finding names, the one that owns the file).

## Root cause

The workflow document and the validator disagree: `0` is the documented value and the validator treats it as absent (most likely a falsy check on the field).

## Proposed action

- Decide which side is right and change the other in the same commit: either accept `0` in the validator as "no owning deliverable", or change triage.md to say "the deliverable that owns the finding's file" and name how to derive it.
- Add a test that a fix task composed exactly as triage.md documents passes `commit-add`.
- Related, same dispatches: fix tasks are created with `envelope_id: null`, so `manage-tasks next` hands out a queued plan task ahead of the fix task (seen three times: TASK-7 before TASK-17, TASK-9 before TASK-18, TASK-11 before TASK-19). The leaves reordered by hand each time.

## Evidence

- aspect: chat_history_analysis - four hand-backs, e.g. "the workflow prescribes deliverable: 0 for fix tasks, but commit-add rejected that with 'Missing required field: deliverable'" and "The triage doc and the manage-tasks validator disagree here".
- aspect: request_result_alignment - 7 fix tasks carry deliverables 1, 2, 5, 3, 4, 5, 5, each chosen by a leaf.
