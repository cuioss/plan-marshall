envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:21:37Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=sweep-the-three-single-instance-defect-classes
source_aspects=logging_gap_analysis,log_analysis

# Emit the [OUTCOME] line before yielding on a voluntary checkpoint

## Context

Phase 5 completed 14 tasks, but only 13 `[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN` lines reached `work.log`. TASK-004 is the unpaired one, and `analyze-logs` reports it independently under two keys — `outcome_pairing.unpaired_completed` and `outcome_for_diffed_tasks.tasks_with_diff_no_outcome` — so the task both reached `status: done` and produced a non-empty diff, yet announced neither.

The dispatch ledger says how it was lost. Of 10 recorded execute dispatches, 6 terminated as `voluntary_checkpoint` and 3 as `budget_yield`; only one reached `clean_exit_queue_empty`. A 60% `voluntary_checkpoint` share is over the 50% threshold the `DISPATCH_TERMINATION_CAUSE` rule sets for agent-initiated re-dispatch, and it is exactly the condition under which a completion line is dropped: the envelope yields between finishing the task and announcing it.

## Root cause

The `[OUTCOME]` emission is not fused to the task-completion write. A dispatch that completes a task and then yields on a voluntary checkpoint can persist the task's `done` status while the completion line is still pending in the yielding envelope, so the record survives and the announcement does not. This is the failure shape lesson `2026-05-08-14-001` already names; this plan is a recurrence of it, not a new class.

## Proposed action

Fuse the emission to the write, the way `manage-status mark-step-done` already fuses the `[STEP] ... Completed step:` marker to the finalize step record: emit `[OUTCOME]` as a side effect of the task-status write rather than as a separate step the yield path can skip. Failing that, make the yield path flush any pending completion line before returning control, and assert the pairing in the loop-exit guard so a gap fails loudly at the boundary instead of surfacing only in a retrospective.

## Evidence

- aspect: logging_gap_analysis — `OUTCOME_COVERAGE`: expected 14, observed 13; `error`-severity finding citing lesson `2026-05-08-14-001`
- aspect: log_analysis — `phase5_logging_gaps.outcome_pairing.unpaired_completed[1]: TASK-004`, and `outcome_for_diffed_tasks.tasks_with_diff_no_outcome[1]: TASK-004`
- aspect: logging_gap_analysis — 5-execute termination distribution: 6 `voluntary_checkpoint`, 3 `budget_yield`, 1 `clean_exit_queue_empty` of 10 rows (60% over the 50% threshold; `budget_yield` correctly excluded from the count)
