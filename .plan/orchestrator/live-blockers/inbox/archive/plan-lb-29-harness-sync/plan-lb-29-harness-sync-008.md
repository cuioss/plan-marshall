envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:35Z

component=plan-marshall:phase-4-plan
category=improvement
created=2026-10-09

# Add an append path to phase-4-plan for deliverables added after task creation

## Context

Plan `plan-lb-29-harness-sync` had 21 pending tasks for 12 deliverables when the operator chose to add the real fixes for two accepted quality-check findings to the plan. Outline was re-entered twice and gained deliverables 13, 14 and 15. The next task-planning dispatch was refused at its re-entry guard: `error: tasks_already_exist`, "Task creation is not idempotent; re-creating would duplicate the queue. To re-plan, clear the existing tasks first". The skill documents no way to append tasks for new deliverables, so all 21 untouched tasks were cleared and 25 were created again.

## Root cause

Task planning has two states only: no tasks, or refuse. The batch creation verb numbers tasks from the start of the array, and the single-task add path is reserved for fix tasks. A plan that legitimately grows by a deliverable before execution starts has no path that keeps the tasks it already has.

## Proposed action

- Add an append mode to phase-4-plan: when every existing task is still pending and each new deliverable has no task, plan only the new deliverables, number their tasks after the highest existing number, wire dependencies against existing tasks, and re-compose the execution manifest once.
- Keep the refusal for every other re-entry.
- Have the refusal name the append mode when its precondition holds.

## Evidence

- aspect: chat_history_analysis — refusal report quoting `tasks_already_exist`, `existing_task_count: 21`; follow-up report "25 tasks across 9 groups" after the re-plan; two outline re-entries for deliverables 13 to 15.
- aspect: plan_efficiency — 4-plan closed twice (`close_count: 2`), 2,348,992 tokens, 881 tool uses, 1h40m wall; 1.0M tokens per deliverable overall.
