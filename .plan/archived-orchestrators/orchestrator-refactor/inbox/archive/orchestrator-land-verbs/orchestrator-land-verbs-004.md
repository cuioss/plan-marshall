envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:42:08Z

component=plan-marshall:execute-task
category=improvement

# Stop per-task verification from blocking on orchestrator-tier module-tests

## Context

In orchestrator-land-verbs, `module-tests plan-marshall` resolved to `execution_tier: orchestrator` on every task (bash_timeout_seconds 616 to 1242, all over the Bash ceiling). Each execute envelope therefore stopped at the first task whose verification named it: 5 of 10 execute dispatches ended as `voluntary_checkpoint` hand-backs, envelope 1 delivered deliverables 1-4 with "no test executed against any of this work", and TASK-8/10/11 were marked done with their new tests unrun. 5-execute cost 2.52M tokens for 13 planned tasks.

## Root cause

Per-task verification lists an orchestrator-tier command that the leaf can never run, so the breakable-test gate turns each task boundary into a round trip to the orchestrator instead of deferring the run to one batched end-of-envelope (or end-of-phase) verification.

## Proposed action

When the live tier of a task's test command is `orchestrator`, record it as owed and continue the envelope (the envelope-1 leaf already did this by hand with an `orchestrator_tier_owed[]` list); the orchestrator then runs one batched module-tests per envelope. Alternatively, have phase-4-plan move orchestrator-tier test commands out of per-task verification into the phase-5 verification sweep.

## Evidence

- aspect: log_analysis — 5-execute dispatch boundaries: 5 voluntary_checkpoint, 2 budget_yield, 1 error, 2 clean_exit_queue_empty
- aspect: logging_gap_analysis — every checkpoint was an orchestrator-tier module-tests hand-back
- aspect: chat_history_analysis — TASK-1, TASK-8, TASK-10, TASK-11 and the PR-fix envelope each returned blocked on module-tests
