envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:03:17Z

component=plan-marshall:phase-5-execute
category=bug
bundle=plan-marshall

# Emit a per-task [ARTIFACT] line at task completion

## Context

Plan `lesson-retirement-fails-open` completed 9 tasks across three
`phase-5-execute` dispatch clusters and emitted 9 matching
`[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN` lines. Every one of
those tasks changed files — the run landed 19 paths across 12 commits.

It emitted zero `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` lines. All 8
`[ARTIFACT]` entries in the whole plan belong to other phases: `request.md` and
the plan record (1-init), `solution_outline.md` (3-outline), TASK-1..3 creation
and `execution.toon` (4-plan), and PR #1113 (6-finalize).

The `ARTIFACT_EMISSION` invariant in
`plan-retrospective/references/logging-gap-analysis.md` states that when at least
one `[OUTCOME]` line exists, every `[OUTCOME]` for a task with a non-empty diff
must be followed by at least one task-scoped `[ARTIFACT]` line. The precondition
holds and the check fails 9 for 9.

The rule's older branch — "zero `[ARTIFACT]` entries when the footprint is
non-empty is an error" — passes, because 8 entries exist. So the coarse branch
reports clean while the specific branch fails completely.

## Root cause

`[OUTCOME]` emission at task completion was instrumented (all 9 lines are present
and correctly paired, `unpaired_completed` and `unpaired_outcome` both empty); the
paired per-task `[ARTIFACT]` emission on the same completion path was not.

## Proposed action

Emit one `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` line naming the task's
changed paths immediately after each `[OUTCOME] Completed TASK-NNN`, on the same
completion path that already emits the `[OUTCOME]`.

## Impact

The per-task file-change record is absent from every plan's work log, so the
`ARTIFACT_EMISSION` invariant cannot pass for any plan, and per-task footprint
attribution has to be reconstructed from commit boundaries instead of read from
the log.

## Evidence

- aspect: logging_gap_analysis — `ARTIFACT_EMISSION` expected 9, observed 0
- aspect: log_analysis — `outcome_pairing.paired: 9`, `unpaired_completed[0]`, `unpaired_outcome[0]`, `counts.artifact_entries: 8`
- artifact: `logs/work.log` — the 8 `[ARTIFACT]` lines are at phases 1, 3, 4 and 6 exclusively
