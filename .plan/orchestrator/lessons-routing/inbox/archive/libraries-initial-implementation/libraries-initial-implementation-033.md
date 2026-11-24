envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:21Z

component=plan-marshall:manage-tasks
category=bug
title=manage-tasks: a loop-back fix task created by the finalize triage can carry empty skills and no verification commands
source_lesson=2026-11-19-19-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# manage-tasks: a loop-back fix task created by the finalize triage can carry empty skills and no verification commands

# Candidate lesson: a loop-back fix task created by the finalize triage carried an empty skills list and no verification commands

- Source signal: plan plan-05-git-core-merge-read-notes (inbox plan-05-git-core-merge-read-notes-006), seen in the task records after the round-2 triage settlement.
- Component: `plan-marshall:manage-tasks` (fix-task creation from triage), `plan-marshall:phase-6-finalize` (wait-region unified triage).

## What happened

TASK-014 ("Fix: second review round on PR 37 ...", origin `fix`, profile `implementation`) was created by the round-2 triage after the commit guard refused the inline edits. Its stored record has `skills[0]` (empty) and `verification.commands[0]` (empty), with only a criteria sentence ("verify -Ppre-commit is green and the second-round review fixes are committed"). The round-1 fix tasks TASK-012 and TASK-013, created by the same triage workflow, each carry six skills (persona-plan-marshall-agent, ref-code-quality, java-core, java-null-safety, javadoc, junit-core) and two verification commands (compile, verify -Ppre-commit). TASK-014 ran correctly only because its edits were already applied and verified in the worktree before the task existed. The record does not show which creation path left the list empty.

## Candidate rule

Resolve skills and verification commands the same way on every fix-task creation path: the skills of the task's profile and domain plus the canonical gate command. At the least, refuse or warn on `origin: fix` with `skills: []` or no verification commands, so a hand-drafted task cannot skip the domain standards when it has real work left to do.
