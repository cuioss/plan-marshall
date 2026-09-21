envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:56Z

# 8 of 9 completed tasks emitted no [ARTIFACT] line

## Context

`analyze-logs` reports `completed_tasks: 9`, `tasks_with_artifacts: 1`, and names the eight that emitted none: TASK-001 through TASK-006, TASK-008, TASK-009. The plan's realized footprint is 25 files, so the tasks demonstrably produced file changes.

`[OUTCOME]` coverage itself is clean — 9 tasks done, 9 `[OUTCOME]` lines, `unpaired_completed` and `unpaired_outcome` both empty — so this is not the re-dispatch loss mode. The tasks completed and announced completion; they just did not announce their artifacts.

## Root cause

The per-task `[ARTIFACT]` emission path was bypassed for nearly every task. Because `[OUTCOME]` pairing is intact, the gap is specific to artifact announcement rather than to task-completion logging generally.

Note that the deterministic floor check could not grade this: with no resolvable footprint the script emitted `ARTIFACT_COVERAGE_UNMEASURABLE` rather than a verdict. The per-task branch is what surfaced the gap, and only after the footprint was recovered by hand could the floor itself be confirmed to pass (`artifact_entries: 14 > 0`).

## Proposed action

Trace why `phase-5-execute` emitted `[ARTIFACT]` for exactly one task, and make the emission part of the same write that records `[OUTCOME]` — the fusion pattern `mark-step-done` already uses for its completion marker — so a task cannot report completion without reporting what it produced.

## Evidence

- aspect: log_analysis — `artifact_emission: completed_tasks 9, tasks_with_artifacts 1`, 8 named
- aspect: log_analysis — `ARTIFACT_EMISSION_PARTIAL` warning
- aspect: logging_gap_analysis — `OUTCOME_COVERAGE` 9/9 paired, so completion logging itself is healthy
- realized footprint: 25 files, so an empty-diff explanation does not hold for all eight
