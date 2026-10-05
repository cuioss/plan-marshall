envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:21:53Z

component=plan-marshall:phase-5-execute
category=bug

# Fix scope_creep_check: its finding type is rejected and its baseline counts upstream commits

## Context

scope_creep_check exited 1 on 9 calls in this plan (script_internal_error, finding_persist_failed: "Invalid finding type: scope_creep_warning"). Every call reported 104-109 residual files, all of them upstream commits merged between plan_creation_sha (59ad113e) and the worktree base, none of them plan work. Execute leaves logged and continued; some raised --threshold to 200 or 100000 just to get a measured result.

## Root cause

Two defects: the guard emits a finding type the findings store does not accept, and the residual set is diffed from plan_creation_sha rather than from the absorbed baseline (main_sha/worktree base), so upstream drift counts as scope creep.

## Proposed action

Register scope_creep_warning in the findings type vocabulary (or emit an accepted type), and diff residuals from the current absorbed baseline so self-absorbed upstream commits are excluded.

## Evidence

- aspect: script_failure_analysis - plan-marshall:phase-5-execute:scope_creep_check check, exit 1, 9 occurrences
- aspect: chat_history_analysis - envelope reports: "finding_persist_failed ... 104 residual files ... upstream commits between plan_creation_sha and the worktree base"
- envelope reports: threshold workarounds --threshold 200 (TASK-10) and --threshold 100000 (TASK-12)
