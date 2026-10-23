envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:51Z

# Execute leaves close a task's last step before its verification runs, so the verification-owed hold is lost

**Component:** plan-marshall:execute-task / plan-marshall:manage-tasks (`finalize-step --verification-owed` / `--verification-complete`)
**Category:** anti-pattern
**Source plan:** plan-14-operator-and-question-stores, from plan-retrospective

## Observation

Leaves closed a task's final step before its verification build ran four times in one plan, with each leaf self-reporting it: TASK-5, TASK-6 and TASK-7, TASK-11, and TASK-14. Each time the task showed `done` while a build was still owed. For TASK-5 the leaf re-finalized with `--verification-owed`. For TASK-11 the flag "can't be added afterwards", so the task stayed `done` with `verification_owed: false` while the module-wide run was still owed. Later wider runs happened to cover them, so the store's `done` was right only by luck.

## Suggested corrective action

- Make the ordering structural: `finalize-step` of a task's last step refuses `done` unless the task's verification has a recorded result, or `--verification-owed` is passed explicitly.
- Or allow `--verification-owed` to be set on a task that is already `done`, so the leaf can repair the record.
- State the order (verify, then finalize the last step) in the execute-task workflow at the step that finalizes the last step.
