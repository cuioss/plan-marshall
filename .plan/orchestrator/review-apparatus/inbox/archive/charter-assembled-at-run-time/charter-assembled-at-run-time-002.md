envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:12:02Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high

# Scope per-task ARTIFACT lines to the task's own diff, not base merges

## Context

In plan `charter-assembled-at-run-time`, the per-task `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` lines attributed files to tasks that never wrote them. TASK-11 (the D8 pilot) listed 30+ files that arrived by merging `origin/main` into the worktree, including `.plan/orchestrator/**` ledger files, `bootstrap_plugin.py`, `marketplace_paths.py` and the shared-harness tests. TASK-14 is a docs task in the foreign settings repository, yet its lines name upstream `.github/workflows/*.yml`, `build.py` and `platform_runtime.py`. TASK-1, TASK-16 and TASK-17 carry byte-identical 11-file lists (TASK-17's CI org-read verbs). The retrospective's ARTIFACT_EMISSION check still passes 8/8, because it counts lines, not correctness.

## Root cause

The per-task change set is diffed over a range that spans merge commits from the base (and, for co-batched tasks, the shared uncommitted working diff), so base-merged files and sibling tasks' files are attributed to the task.

## Proposed action

Compute the Step-8 artifact set over the task's own first-parent range, from its start SHA to its commit, excluding merge commits whose second parent is on `origin/{base}`. When tasks share one per-deliverable commit, attribute each file only to the task whose steps target it. Tasks that edit a foreign repository (`--project-dir`) should emit their foreign paths. They should never inherit the host worktree's diff. Add a test with a merge-from-base in the task range, asserting that the merged files are absent from the task's artifacts.

## Evidence

- aspect: logging_gap_analysis: TASK-11/TASK-14 attributed upstream-merged files; identical TASK-1/16/17 lists
- aspect: log_analysis: `artifact_emission` eligible 8 / with artifacts 8, so the count passes over wrong content
