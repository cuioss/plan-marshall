envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:15Z

component=plan-marshall:phase-5-execute
category=improvement
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Persist each task's changed_files so per-task artifact emission stays measurable

## Context

The logging-gap aspect's strongest check — ARTIFACT_EMISSION, which asks what fraction of change-qualified completed tasks emitted at least one per-task `[ARTIFACT]` line — could not run at all on this plan. `change_attribution` came back `unavailable` with the reason that no completed task record carries a `changed_files` list. The check that would independently have caught this plan's real emission gap was disabled by missing data, and the gap surfaced only through the weaker OUTCOME_COVERAGE rule.

## Root cause

phase-5-execute Step 8 already computes each task's diff against its `task_start_sha` in order to decide whether to emit `[ARTIFACT]` at all. That diff is used for the branch decision and then discarded. Nothing persists it, and the per-task SHA range is not written anywhere stable, so an offline reader has no way to reconstruct which tasks changed files.

## Proposed action

Write the computed diff to the task record as a `changed_files` list at the point Step 8 already holds it. A present-but-empty list is a measurement ("this task changed nothing") and is what makes a compliant no-op task distinguishable from an unrecorded one — which is precisely the distinction the ARTIFACT_EMISSION population rule needs in order to qualify M and N honestly.

## Evidence

- aspect: logging_gap_analysis — `change_attribution: unavailable`, reason "no completed task record carries a changed_files list"; the eligible-task keys are absent rather than zero, so the rule correctly emitted no finding and correctly reported that it could not look
- aspect: log_analysis — artifact_emission.completed_tasks 13, tasks_with_artifacts 7, tasks_without_artifacts [TASK-003, TASK-005, TASK-007, TASK-010, TASK-012, TASK-013]; without change qualification none of those six can be told from a compliant no-op
- aspect: llm_to_script_opportunities — complexity low, the value is already computed and thrown away
