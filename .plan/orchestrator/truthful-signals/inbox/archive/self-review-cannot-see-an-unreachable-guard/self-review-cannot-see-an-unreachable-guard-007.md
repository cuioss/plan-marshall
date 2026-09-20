envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:16:52Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-07-29

# Per-task [ARTIFACT] emission stops after the first per-deliverable commit batch

## Context

On plan `self-review-cannot-see-an-unreachable-guard`, all 8 tasks (TASK-001..TASK-008) completed
with non-empty diffs and each emitted a matching `[OUTCOME] (plan-marshall:phase-5-execute)
Completed TASK-NNN` line. Only TASK-001 (`19:19:28`) and TASK-002 (`19:29:06`) also carry a
matching `[ARTIFACT] (plan-marshall:phase-5-execute:N)` line naming the files touched. TASK-003
through TASK-008 are traceable only via three batched `Per-deliverable commit: ...` `[OUTCOME]`
lines that name commit SHAs and task ranges, never per-task file lists.

## Root cause

The `logging-gap-analysis` ARTIFACT_EMISSION rule expects every `[OUTCOME]`-with-changes line to
be immediately followed by a matching `[ARTIFACT]` line. The observed pattern (2 of 8 covered)
suggests the per-task `[ARTIFACT]` emission call is only reached on a code path exercised early in
the envelope (the first task or two before a voluntary-checkpoint yield), and is skipped once the
execution re-enters after a yield or moves to batched per-deliverable commits.

## Proposed action

Audit `plan-marshall:execute-task` / `plan-marshall:phase-5-execute`'s task-completion path for the
call site that emits `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` and confirm it fires on every
task completion, including tasks completed after a voluntary-checkpoint re-entry and tasks folded
into a batched per-deliverable commit.

## Evidence

- aspect: logging-gap-analysis — `ARTIFACT_EMISSION,8,2` (`expected_vs_actual`); gap detail names
  TASK-003..TASK-008 as missing per-task `[ARTIFACT]` lines
- work.log: `[OUTCOME]` lines at 19:18:08, 19:27:04, 19:36:43, 19:45:09, 19:45:31, 19:50:02,
  21:05:54, 21:12:39 (8 total) vs `[ARTIFACT]` lines only at 19:19:28 and 19:29:06 (2 total)
