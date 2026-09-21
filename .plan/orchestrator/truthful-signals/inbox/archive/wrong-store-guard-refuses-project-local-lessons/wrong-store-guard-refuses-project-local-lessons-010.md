envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:00:00Z

# Emit [ARTIFACT] lines after phase-5-execute task completion

component: plan-marshall:phase-5-execute
category: bug
confidence: medium
source_plan: wrong-store-guard-refuses-project-local-lessons

## Context

TASK-001, TASK-002, and TASK-003 all reached `[OUTCOME] (plan-marshall:phase-5-execute) Completed` in
`work.log`, and all three genuinely wrote files (the plan's realized footprint is exactly the 4 files
these tasks touched). No `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` line follows any of the 3
`[OUTCOME]` lines — the only `[ARTIFACT]` entries in this plan's `work.log` come from phase-1-init,
phase-3-outline, and phase-4-plan (request/plan/outline/task creation), none from phase-5-execute task
completion.

## Root cause

The `logging-gap-analysis` ARTIFACT_EMISSION rule (precondition-guarded on an `[OUTCOME] Completed` line
existing) expects one `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` line per task that produced file
changes. This plan tripped that rule at 3/3 — every completed task with a diff is missing its paired
artifact announcement.

## Proposed action

Confirm whether this plan's execution path (which ran phase-5-execute driven INLINE after a blocked
dispatched-leaf cwd-pinning failure, per `decision.log` `[WARNING] cwd_pinning_impossible_in_dispatched_leaf`)
skips the `[ARTIFACT]` emission that the normal dispatched execute-task path performs — if so, the inline
fallback path in `execute-task` / `phase-5-execute` needs the same emission added.

## Evidence

- aspect: logging-gap-analysis — ARTIFACT_EMISSION rule: `outcome_with_changes=3`,
  `artifacts_after_outcome=0`.
