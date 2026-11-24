envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:16Z

component=plan-marshall:manage-change-ledger
category=bug
title=change-ledger holds no build-duration row for Maven builds, so the retrospective build time is unavailable
source_lesson=2026-11-19-06-005
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# change-ledger holds no build-duration row for Maven builds, so the retrospective build time is unavailable

# Candidate lesson: the change-ledger holds no build-duration row for a plan that ran 36 Maven builds

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-014), plan-retrospective (log-analysis build_time block), confidence medium (one plan, cause not traced).

## What happened

The retrospective's build-time oracle reads build rows from the change-ledger. The ledger was present and readable with 14 rows, but `summed_rows: 0` and `build_count: 0`, so `total_build_seconds` is `unavailable`. The script log shows 36 `plan-marshall:build-maven:maven` calls (1,719,700 ms cumulative, 31% of script time), and the phase-5 freshness gate reported `basis=ledger-verified, matched_notation=plan-marshall:build-maven:maven` twice.

## Root cause

Not traced. Either Maven builds append no build row of the shape `summarize_build_ledger` counts, or they append rows without `duration_seconds`. The freshness gate finds something it accepts, so the two readers may disagree on the row shape.

## Candidate rule

Check which ledger rows the freshness gate matched and why `summarize_build_ledger` counted none; make Maven build rows carry a duration so build time is measured for Maven plans.


## Recurrence in a later plan (plan-05-git-core-merge-read-notes, inbox plan-05-git-core-merge-read-notes-010)

- Source signal: retrospective log-analysis `build_time` block and logging-gap analysis (BUILD_LEDGER gap), component `plan-marshall:build-maven` with `plan-marshall:manage-change-ledger` as the receiving store.
- Evidence: 45 `plan-marshall:build-maven:maven` calls in `script-execution.log`, about 2,189 s in total and 52% of all script time. The change-ledger was readable and held 14 rows for the plan, none of them a build row (`summed_rows: 0`), so `build_time.total_build_seconds` is `unavailable` and the build-count reconciliation reports the ledger as unmeasured.

Same root cause and same corrective rule: the maven `run` wrapper (or the call site meant to record its outcome) writes no `kind=build` ledger row. Have `run` append one row per invocation (command, duration_seconds, status), or document which caller owns the append, and add a check that a plan with logged build calls and zero ledger build rows produces a finding.


## Recurrence in a later plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-025)

- Source signal: plan-retrospective (log-analysis and plan-efficiency aspects). The script log shows 50 `plan-marshall:build-maven:maven` calls, 3.24M ms, 42% of all script time, but the change-ledger (present, 16 rows scanned) holds no build row for the plan, so the retrospective reports build time as unavailable and cannot reconcile the build count.
- Same root cause and rule: the maven wrapper appends a build row (command, status, duration) for each run, and the rows written in a worktree are carried into the main checkout when the plan integrates, so build time survives the worktree's removal.


## Recurrence in a later plan (plan-20-leftover-fixes-2, inbox plan-20-leftover-fixes-2-019)

65 `build-maven:maven` calls (about 4,540 s, 29.6% of script time) while the change ledger, present and readable with 16 rows, held no build row with a duration (`summed_rows` 0), so `total_build_seconds` was `unavailable` and the build-count reconciliation gave no verdict. The execute freshness gate did match a row ("ledger row 127 ... written by your verify -Ppre-commit run"), but that row lives in the worktree's ledger; the retrospective runs on the main checkout after the worktree is removed. Either build rows land in a ledger that does not survive the worktree, or the worktree's older script runner (see 2026-11-23-14-010) writes them in a form the reader does not count. Check where build rows land during a worktree plan and whether integrate-into-main carries them back.
