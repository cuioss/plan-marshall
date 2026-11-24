envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:09Z

component=plan-marshall:execute-task
category=bug
title=Chain-tail commit never fires on linear task chains that cross a deliverable boundary
source_lesson=2026-11-18-13-007
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Chain-tail commit never fires on linear task chains that cross a deliverable boundary

# Candidate lesson: the chain-tail commit never fires on linear task chains that cross a deliverable boundary

- Source signal: plan-retrospective, plan git-core-import (inbox git-core-import-009).

## What happened

The plan had a linear chain TASK-1 to TASK-8, each task depending on the one before it, across four deliverables. Execute envelopes 1 and 2 both reported that the chain-tail check ("no pending task depends on the finished task") never fires for a deliverable's last task, because the next deliverable's first task depends on it. Read literally, no commit would happen until the end of the whole chain. Both envelopes departed from the rule on their own and committed at each deliverable end.

## Root cause

The commit predicate is keyed on task dependencies, not on deliverable completion.

## Candidate rule

Commit when every task of a deliverable is done, or treat a dependant in a different deliverable as not blocking the chain-tail. Add a fixture with a linear cross-deliverable chain.
