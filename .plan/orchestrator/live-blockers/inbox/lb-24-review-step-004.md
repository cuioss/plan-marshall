envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:57:55Z

component=plan-marshall:phase-5-execute
category=bug

# Make scope_creep_check persist a finding type the findings store accepts

## Context

In plan lb-24-review-step `scope_creep_check check` exited 1 on every task (22 recorded failures across 5-execute and both review-fix re-entries) with `finding_persist_failed`. The findings store rejects type `scope_creep_warning`; its accepted set is bug, improvement, anti-pattern, triage, tip, insight, best-practice, build-error, test-failure, lint-issue, sonar-issue, arch-constraint, pr-comment, pr-comment-overflow. The measured residual (66 to 281 files, mostly upstream commits absorbed after plan creation) was never stored anywhere but the ERROR log line.

## Root cause

The producer and the store disagree on the finding-type vocabulary, and no test exercises the persist path end to end against the real store.

## Proposed action

Either register `scope_creep_warning` in the findings store's type set or have the guard emit an accepted type. Add a test that runs the guard against the real store and asserts the finding is persisted. Separately, measure the residual against the worktree's own merge base rather than `plan_creation_sha`, so absorbed upstream commits stop counting as scope creep.

## Evidence

- script-failure-analysis: plan-marshall:phase-5-execute:scope_creep_check, script_internal_error, 22 occurrences
- work.log ERROR 5b10d1: Invalid finding type: scope_creep_warning
- every execute hand-back from TASK-1 to TASK-25 reported the same failure
