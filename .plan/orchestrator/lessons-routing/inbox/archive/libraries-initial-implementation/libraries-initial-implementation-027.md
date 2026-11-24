envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:17Z

component=plan-marshall:phase-5-execute
category=improvement
title=phase-5: state the per-deliverable commit trigger in deliverables, the dependency-graph rule never fires on a linear task chain
source_lesson=2026-11-19-06-006
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# phase-5: state the per-deliverable commit trigger in deliverables, the dependency-graph rule never fires on a linear task chain

# Candidate lesson: the phase-5 per-deliverable commit rule never fires on a linear task chain

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-015), plan-retrospective (chat-history), confidence medium.

## What happened

Phase-4 produced a strict chain of 10 tasks, each depending on the previous one because deliverables 1-4 share the same three files. The documented commit rule ("commit when no pending task depends on the finished task") never fires on such a chain, so the executing agent committed at each deliverable boundary on its own judgement. The result was right but rests on agent judgement, not on the workflow.

## Root cause

The trigger is phrased in terms of the task dependency graph; a chain never satisfies it before the last task, which would collapse the whole plan into one commit.

## Candidate rule

State the trigger in terms of deliverables: commit when the last task of a deliverable is done (all tasks carrying that deliverable number), independent of cross-deliverable dependencies.


## Recurrence in a later plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-022)

- Source signal: plan-retrospective (chat-history aspect, envelope 1 hand-back). Phase 4 created 9 tasks as one strict chain, including the first task of each deliverable depending on the last task of the previous one (TASK-3 on TASK-2, TASK-5 on TASK-4, ...). The execute commit rule commits a deliverable at its chain tail, so read literally it never fired for deliverable 1; the executor improvised by treating a cross-deliverable dependency as non-blocking for the commit.
- Same root cause: the planner encodes deliverable order as `depends_on` edges between tasks of different deliverables. Order deliverables through execution order or envelope packing and add only real data dependencies across deliverables, or define the commit rule as "last task of the deliverable done" and state it in the execute workflow so leaves do not each improvise it.
