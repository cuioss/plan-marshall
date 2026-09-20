envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:03:09Z

component=plan-marshall:phase-5-execute
category=improvement
confidence=medium
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Emit [ARTIFACT] from the task-completion path, not from the task body

## Context

```
artifact_emission:
  completed_tasks: 19
  tasks_with_artifacts: 4
  tasks_without_artifacts: 15
```

Four of nineteen completed tasks emitted at least one `[ARTIFACT]` line. The plan's
merged footprint is 28 files across those 19 tasks, so the documented benign
explanation — "a completed task with an empty diff legitimately emits nothing" —
cannot account for 15 of them.

## Root cause

Emission depends on the task body remembering to log. That makes artifact coverage a
property of authoring discipline rather than of the structural fact that matters:
a task completed and left a non-empty diff.

## Proposed action

Emit `[ARTIFACT]` from the task-completion path, derived from the task's own diff, so
that coverage is guaranteed by construction. If per-task diffs are not available at
that point, publish the emitting population beside the count — `4 of 19` is
currently reported without saying how many of the 15 had an empty diff, which is the
one number that would separate a real gap from a benign one.

## Why it matters

The gap is invisible while the plan runs and surfaces only at retrospective, by which
point the per-task attribution it would have supplied is unrecoverable. This plan's
own scope-growth analysis had to be reconstructed from the merged commit rather than
read from per-task artifact records.

## Evidence

- aspect log_analysis: `artifact_emission`, and the emitted
  `ARTIFACT_EMISSION_PARTIAL` warning
- merged footprint: 28 files across 19 completed tasks
