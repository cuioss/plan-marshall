envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:41:04Z

component=plan-marshall:phase-5-execute
category=bug

# Make scope_creep_check persistable and diff it against the merge base

## Context

`scope_creep_check check` exited 1 with `finding_persist_failed` on every task of orchestrator-land-verbs (8 recorded failures across TASK-1, 2, 9, 11, 12 and the PR-fix envelope). `manage-findings` rejects the finding type `scope_creep_warning`, so the guard never records anything. Its residual count (110, 116, 118, 141 across the run) was dominated by upstream main commits, because it diffs `plan_creation_sha..HEAD` and `plan_creation_sha` (0a099a107) predates the worktree's base (8aa33cfe1) and every later rebase.

## Root cause

Two defects in one guard: an unregistered finding type, and a diff base taken from plan creation instead of the merge base.

## Proposed action

Register the finding type (or map it onto an accepted one) and diff against `git merge-base origin/{base} HEAD`. Recurrence of active lessons 2026-10-02-10-003 and 2026-10-02-10-004 — merge into them rather than filing new.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:phase-5-execute:scope_creep_check check`, script_internal_error, 8 occurrences
- aspect: chat_history_analysis — six separate execute hand-backs report `finding_persist_failed` and the inflated residual
- aspect: log_analysis — errors_work 26, errors_script 14
