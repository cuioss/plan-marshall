envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-60-lb-40-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T10:37:44Z

component=plan-marshall:phase-5-execute
category=improvement
title=Emit an OUTCOME line for every completed task, including the last envelope's

# Emit an OUTCOME line for every completed task

## Context

Plan `implement-plan-lb-60-lb-40-regression-fixes` completed 12 tasks but
`work.log` carries only 11
`[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN` lines. TASK-002
completed with a non-empty diff and emitted neither an `[OUTCOME]` line nor a
per-task `[ARTIFACT]` line. The same task is the sole entry in both
`tasks_without_artifacts` and `tasks_with_diff_no_outcome`.

## Root cause

An agent-initiated re-dispatch boundary: the dispatch that finished TASK-002
terminated without emitting the per-task completion line, which is exactly the
loss pattern lesson `2026-05-08-14-001` describes. The plan's 5-execute phase
recorded 3 re-entries and 4 `voluntary_checkpoint` terminations, so a completion
landed in a boundary the guard did not cover.

## Proposed action

Confirm the `[OUTCOME]` guard fires on every completed task regardless of which
dispatch envelope completed it, and extend the guard to the re-entered
dispatch path if it does not.

## Evidence

- aspect: logging_gap_analysis — `OUTCOME_COVERAGE` error, 11 of 12 completed tasks carried an `[OUTCOME]` line; gap detail names TASK-002
- aspect: log_analysis — `artifact_emission.tasks_without_artifacts: [TASK-002]`; `phase5_logging_gaps.outcome_for_diffed_tasks.tasks_with_diff_no_outcome: [TASK-002]`
- aspect: script_failure_analysis — not implicated (no script failure for TASK-002)
