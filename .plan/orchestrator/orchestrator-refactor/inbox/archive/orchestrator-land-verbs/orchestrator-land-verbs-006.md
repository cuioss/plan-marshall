envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:42:51Z

component=plan-marshall:plan-marshall
category=bug

# Record daemon-routed builds against the owning plan

## Context

orchestrator-land-verbs logged 69 `pyproject_build` calls in its script log, yet the change-ledger (925 rows scanned) holds no build row for the plan, so the retrospective's build-time oracle reports `unavailable`. The PR-fix execute leaf noted that "every build reply says plan=NO_PLAN (daemon-routed, logs under the main checkout's NO_PLAN/build-results)".

## Root cause

Builds routed through the build daemon are attributed to `NO_PLAN` instead of the plan whose worktree they ran in, so neither the change-ledger build row nor the plan's build-results directory receives them.

## Proposed action

Recurrence of active lesson 2026-10-02-10-009 — merge into it. Add the observation that the attribution loss is not limited to orchestrator-tier verify runs: per-task compile, test-compile and quality-gate calls from inside execute leaves were also recorded as NO_PLAN.

## Evidence

- aspect: log_analysis — build_time.summed_rows 0, ledger_rows_scanned 925, log_build_calls 69
- aspect: plan_efficiency — total_build_seconds unavailable
- aspect: chat_history_analysis — PR-fix execute hand-back: build replies say plan=NO_PLAN
