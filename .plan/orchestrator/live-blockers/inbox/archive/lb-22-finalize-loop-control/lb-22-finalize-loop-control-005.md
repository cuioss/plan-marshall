envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:01Z

component=plan-marshall:plan-marshall
category=bug
source_plan=lb-22-finalize-loop-control
confidence=high

# Give triage fix tasks a deliverable value manage-tasks accepts

## Context

`plan-marshall/workflow/triage.md` prescribes `deliverable: 0` for a fix task. `manage-tasks commit-add` rejects that value with "Missing required field: deliverable". Three separate triage runs in this plan hit the rejection and each chose a real deliverable number by its own reasoning: 7 (the deliverable whose commit introduced the flagged line), 4 (the deliverable that owns the file), and 8 and 10 (matching the earlier fix tasks).

## Root cause

The workflow document and the script disagree. The script appears to treat `0` as an absent value, so the documented marker for "not part of any deliverable" cannot be stored.

## Proposed action

Decide which side is right and align the other:

- if a fix task should stand outside the deliverable chain, make `commit-add` accept an explicit fix-task marker (and stop treating `0` as missing); or
- if a fix task should attach to a deliverable, replace `deliverable: 0` in `triage.md` with the rule for picking it (for example: the deliverable whose commit introduced the defect).

The choice matters beyond the call shape: the deliverable number decides which per-deliverable commit and change-ledger entry a fix lands in, and three agents currently decide that three different ways.

## Evidence

- aspect: chat_history_analysis - three triage hand-backs list the rejection under deviations (TASK-21 -> deliverable 7, TASK-23 -> deliverable 4, TASK-24/25 -> deliverables 8 and 10).
- source: the literal `deliverable: 0` is still present in `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` at main `6b00815e0` (one match; one more in `test/plan-marshall/manage-tasks/test_manage_tasks_add.py`, not inspected).
