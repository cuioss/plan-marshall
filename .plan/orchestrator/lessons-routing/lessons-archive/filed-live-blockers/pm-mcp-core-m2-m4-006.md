envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:55Z

# Candidate lesson: Fix tasks created by the finalize triage carry no envelope id and no cost size

- Component: plan-marshall:phase-5-execute
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-014 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during plan primitive-spi-and-validators. Not confirmed from the records this step read.

## What happened (as reported by the orchestrator)

The tasks the finalize triage created for the review and Sonar findings (TASK-10 to TASK-17) carry `envelope_id` null and no cost size. The execute phase hands tasks over in groups keyed by envelope. With no key on the fix tasks, the hand-off had to be told by prompt to run them as one group.

## Verification of the wording

- NOT confirmed: the decision log has no entry about a null `envelope_id` or a missing cost size.
- The task read of TASK-10 (`manage-tasks read`) shows `origin: fix` and no envelope or cost field at all; the same read of TASK-2 (`origin: plan`) shows none either, so this view cannot tell the two apart.
- Consistent with it: the decision log shows the envelope-keyed hand-off for planned tasks (6f0cde: "envelope 1 exhausted after TASK-6; next pending task TASK-7 belongs to envelope 2") and no such line for the three loop-back rounds.

## Proposed rule

A task created outside the plan phase gets an envelope id and a cost size at creation, or the execute phase has a stated default for tasks without one (for example: all fix tasks of one loop-back round form one group).

## Evidence

- Decision log 6f0cde; loop-back entries 168311 (three times).
- `manage-tasks read` of TASK-10 and TASK-2.
