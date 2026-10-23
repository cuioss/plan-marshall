# A task closes before its verification runs, so the verification-owed hold is lost

Severity: high. Bundle: **plan-marshall** (`execute-task`, `manage-tasks`). Filed under RULING 2026-10-09 (a).

Recurrence: two plans, six leaves, each self-reporting it.

## Sources

- inbox `pm-mcp-core-m2-m4-294`, `-352`
- related but graded separately: `-318` (`--verification-owed` flag absent from the parser)

## Consolidated statement

Finalizing a task's **last step** auto-completes the task, independent of whether the task's verification has run and passed.

- `TASK-001`: work log shows `step 1 done` at 14:26:13Z and `Completed TASK-001` at 14:26:22Z, while `maven compile -pl pm-core -am` only started at 14:26:49Z. The compile was green, so no harm followed — a red verification would have met a task already recorded `done`.
- Four leaves in another plan closed a task's final step before the build ran (TASK-5, -6, -7, -11, -14). For TASK-5 the leaf re-finalized with `--verification-owed`; for TASK-11 the flag "can't be added afterwards", so the task stayed `done` with `verification_owed: false` while a module-wide run was still owed. Later wider runs covered them by luck.

## What is asked

- Keep a task `in_progress` after its last step until its verification result is recorded; or have the step-done verb refuse to auto-complete a task that declares a verification command with no recorded result, unless `--verification-owed` is passed explicitly.
- Allow `--verification-owed` to be set on a task that is already `done`, so a leaf can repair the record.
- Emit the `[OUTCOME] Completed` line only after verification, and state the order (verify, then finalize the last step) in the execute-task workflow at the step that finalizes the last step.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
