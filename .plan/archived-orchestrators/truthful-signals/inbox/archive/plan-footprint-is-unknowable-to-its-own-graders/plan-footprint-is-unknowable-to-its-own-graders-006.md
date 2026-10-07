envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:40Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# [ARTIFACT] emission covered 6 of 16 completed tasks

## Context

`phase-5-execute` is expected to emit at least one `[ARTIFACT]` work-log line per task that produced file changes. On this plan, 6 of 16 completed tasks emitted one or more; **10 emitted none**:

TASK-001, 002, 003, 004, 007, 008, 010, 011, 012, 013.

A completed task with an empty diff legitimately emits nothing, so the count alone is not proof. It is not the explanation here: TASK-001 declares ten `write-replace` steps, and **all ten of its target paths appear in the realized 33-path footprint**.

## Root cause

The emitting path is bypassed on some execution route. The surrounding invariants are all clean, which narrows it: `[OUTCOME]` pairing is 16/16, `tasks_with_diff_no_outcome` is empty, and re-entry clustering matches (4 expected, 4 observed). So tasks completed, were recorded as completed, and were known to have diffs — and still emitted no artifact line.

## Proposed action

Trace the `[ARTIFACT]` emission site against the task-completion path and establish which route skips it. The three clean sibling invariants above bound the search: whatever the route is, it still emits `[OUTCOME]` correctly.

## Evidence

- aspect: log_analysis — `artifact_emission: completed_tasks: 16, tasks_with_artifacts: 6, tasks_without_artifacts[10]`; finding `ARTIFACT_EMISSION_PARTIAL`.
- aspect: logging_gap_analysis — `ARTIFACT_EMISSION` expected_min 16, observed 6.
- Plan totals: 21 `[ARTIFACT]` entries against 682 work-log entries and 16 completed tasks.
- TASK-001 target paths cross-checked against `references.realized_footprint` (33 paths, tier-2 resolved, tier-3 confirmed identical): all 10 present.
