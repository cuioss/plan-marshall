envelope_version=1
sender_type=plan
sender_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T16:20:24Z

component=plan-marshall:phase-5-execute
category=bug
title=Recurrence: scope_creep_check still persists a finding type manage-findings rejects

# Recurrence: scope_creep_check still persists a finding type manage-findings rejects

## Context

During plan the-comment-pipeline-on-the-way-in (PLAN-PR-067), `plan-marshall:phase-5-execute:scope_creep_check check` failed 10 times with exit 1 and `finding_persist_failed`: it writes finding type `scope_creep_warning`, which is not in the manage-findings type set. Each failure also reported a 44-file residual that came from upstream commits absorbed by the finalize rebase, not from the task being checked.

## Root cause

`scope_creep_check.py` (and its SKILL.md and test pins) still use the type literal `scope_creep_warning`, while manage-findings accepts only its declared type tuple. The diff base is `plan_creation_sha`, so absorbed upstream commits count as residual.

## Proposed action

Route this as a recurrence, not as a new lesson. The active lessons store already carries three lessons with this root cause (2026-09-22-15-001, 2026-09-23-16-001, 2026-09-24-09-001). Merge them into one and stage the fix: persist an accepted finding type, and move the diff base to the post-rebase worktree base.

## Evidence

- aspect: script_failure_analysis: `scope_creep_check check` script_internal_error, 10 occurrences, first 2026-09-23T17:08:41Z
- aspect: log_analysis: work.log ERROR lines "Invalid finding type: scope_creep_warning" (e.g. 2026-09-24T08:45:04Z, 13:28:45Z)
- architecture search: `scope_creep_warning` appears in phase-5-execute/scripts/scope_creep_check.py (4), phase-5-execute/SKILL.md (3), test_scope_creep_check.py (4), test_qgate_persist_contract.py (1)
