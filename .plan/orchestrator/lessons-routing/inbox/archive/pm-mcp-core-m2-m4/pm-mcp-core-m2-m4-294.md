envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:17Z

# Do not complete a task before its verification ran

Component: plan-marshall:manage-tasks
Category (proposed): bug
Source: plan spend-removal, retrospective (execute envelope 1 report and work log)

## Context

TASK-001 had two steps. The work log shows `TASK-001 step 1 done` at 14:26:13Z and `Completed TASK-001` plus its `[OUTCOME]` line at 14:26:22Z, while the task's verification (`maven compile -pl pm-core -am`) only started at 14:26:49Z. The execute envelope reported it: "Marking its last step done also marked the task done before its verification ran." The compile was green, so no harm followed here, but a red verification would have met a task already recorded as done.

## Root cause

Completing the last step of a task auto-completes the task, independent of whether the task's verification has run and passed.

## Proposed action

- Keep a task `in_progress` after its last step until its verification result is recorded, or have the step-done verb refuse to auto-complete a task that declares a verification command with no recorded result.
- Emit the `[OUTCOME] Completed` line only after verification, so the work-log order matches the real order.

## Evidence

- aspect: chat_history_analysis - execute envelope 1: "TASK-1 closed early. Marking its last step done also marked the task done before its verification ran."
- aspect: log_analysis - work.log: Completed TASK-001 at 14:26:22Z precedes "[ATTEMPT] TASK-1 verification: maven compile -pl pm-core -am" at 14:26:49Z.
