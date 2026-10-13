envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:22Z

component=plan-marshall:manage-tasks
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Keep a module_testing task open until its deferred tests have run

## Context

In 5-execute of lb-25-phase-and-merge-gates, `module-tests plan-marshall` resolved to the orchestrator tier, so test tasks had to hand the build back. Each time, `finalize-step` closed the task as `done` the moment its last step was marked, before any of its tests ran: TASK-14 (the leaf set it back to in_progress by hand), TASK-15 (left done with its breakable-test gate unrun), and TASK-17/18/19/20. A failure in the deferred run would then have to be traced back to a task already recorded done.

## Root cause

`manage-tasks finalize-step` auto-completes a task on its last step and has no notion of a pending verification the task's profile still owes.

## Proposed action

Do not auto-close a task whose verification is still pending (a module_testing task, or any task with an orchestrator-tier gate not yet run); either keep it in_progress until the verification result is recorded, or record an explicit `verification: pending` state that loop-exit-guard and the execute-exit checks refuse to pass.

## Evidence

- aspect: chat_history_analysis - "finalize-step closed TASK-14 automatically after its last step. I set it back to in_progress, because a module-testing task can't count as done until its tests run"
- aspect: chat_history_analysis - "TASK-15 shows done: marking its last step done closed it automatically. Its test check ... has not run yet"
- aspect: chat_history_analysis - "finalize-step marked TASK-18, 19 and 20 done as soon as their last step closed, before the test runs"
