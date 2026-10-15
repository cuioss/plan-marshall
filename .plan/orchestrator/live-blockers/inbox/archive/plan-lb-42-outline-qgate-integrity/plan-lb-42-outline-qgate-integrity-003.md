envelope_version=1
sender_type=plan
sender_id=plan-lb-42-outline-qgate-integrity
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T11:36:46Z

component=plan-marshall:phase-5-execute
category=improvement
title=Keep [OUTCOME] coverage complete for diffed tasks
source_plan=plan-lb-42-outline-qgate-integrity
confidence=medium

# Keep [OUTCOME] coverage complete for diffed tasks

## Context

The plan-lb-42-outline-qgate-integrity retrospective paired 8 [OUTCOME] lines against 10 completed tasks; TASK-002 and TASK-003 carried diffs with no outcome line, and only 8 of 10 completed task records carried a changed_files list, so change attribution was unavailable.

## Root cause

Outcome emission and per-task change recording are written by independent call sites with no shared transaction, so a task can land a diff without either record.

## Proposed action

Have the execute-task completion path emit the [OUTCOME] line and the changed_files list from the same post-step hook so the two populations cannot diverge.

## Evidence

- aspect: logging_gap_analysis — OUTCOME_COVERAGE 8 of 10; tasks_with_diff_no_outcome TASK-002, TASK-003
- aspect: log-analysis — outcome_pairing paired 8; change_attribution unavailable
