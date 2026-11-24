envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:15Z

component=plan-marshall:phase-5-execute
category=bug
title=phase-5 completion line counts the envelope's tasks against the plan total (4/10, 1/11 with every task done)
source_lesson=2026-11-19-06-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# phase-5 completion line counts the envelope's tasks against the plan total (4/10, 1/11 with every task done)

# Candidate lesson: the phase-5 completion line counts the tasks of the current envelope against the plan's total

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-012), plan-retrospective (logging-gap-analysis, log-analysis), confidence high.

## What happened

After envelope 2 finished every remaining task, phase-5-execute logged `Execute phase complete — 4/10 tasks done`; after the loop-back fix envelope it logged `1/11 tasks done`. In both cases every task was done (10/10, then 11/11).

## Root cause

The numerator is the number of tasks completed by the current dispatch, the denominator the plan's total task count. On any multi-envelope or loop-back run the line reads as an incomplete phase.

## Candidate rule

Compute the numerator from the task store (tasks with status done), or label the two numbers separately, for example `11/11 tasks done (1 in this envelope)`.
