envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:50Z

component=plan-marshall:marshall-steward
category=bug
created=2026-10-18

# Detect executor and workflow-doc version skew before a plan runs

## Context

During plan-20-job-runner `.plan/execute-script.py` was pinned to plugin 0.1.1916 while the leaves followed workflow docs from 0.1.1948. Verbs and flags the docs prescribe were rejected: `manage-solution-outline deliverable-hashes` (unknown_verb, 3 times, so no Q-Gate re-validation skip was possible), `git-workflow commit` (unknown_verb, leaves fell back to plain `git commit`), `manage-tasks finalize-step --verification-owed` (unknown flag, so TASK-16 was marked done without its verification hold) and `manage-tasks commit-add` refusing `deliverable: 0` with `origin: fix` (fix tasks 20 to 25 were filed under deliverable 4 or 6 instead).

## Root cause

Nothing compares the executor's pinned plugin version with the version of the skill docs the session loads, so a stale executor surfaces only as scattered argparse rejections and silent fallbacks inside leaves.

## Proposed action

Have the executor (or phase-1-init) compare its pinned version with the loaded plugin version and fail or warn with the steward `upgrade` remedy when they differ, before any phase dispatch.

## Evidence

- aspect: script-failure-analysis - deliverable-hashes argparse rejection x3, manage-tasks finalize-step x2, 16 failures over 8 signatures
- aspect: chat_history_analysis - triage leaf: "executor pinned to plugin 0.1.1916, while the workflow docs I followed are 0.1.1948"; envelope reports of unknown_verb for git-workflow commit and unknown_flag for --verification-owed
