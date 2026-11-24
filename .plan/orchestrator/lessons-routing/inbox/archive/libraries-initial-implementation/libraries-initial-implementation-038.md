envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:25Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: never point at an unrecorded question, and check an external-format content decision against the format's schema before freezing it
source_lesson=2026-11-20-07-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# phase-3-outline: never point at an unrecorded question, and check an external-format content decision against the format's schema before freezing it

# Candidate lesson: an outline pointed at a question it never recorded, and the owner's decision on an external file format was taken on an unverified assumption

- Source signal: plan implement-plan-06-build-guards (inbox implement-plan-06-build-guards-004), Q-Gate finding 5ecc43 (phase 3-outline, request alignment, severity warning), resolution `taken_into_account`, with an execute-phase follow-on.

## What happened

Deliverable 3's "Change per file" for `git-worktrees` said the files would carry empty arrays "(see the batched question on this point)", but no such question existed anywhere in `solution_outline.md`; whether `git-worktrees` ships empty metadata files or none was open and untraceable. The owner decided on empty arrays and the outline carried the decision into three deliverables.

In execute, TASK-8 found that an empty array is not a valid `resource-config.json`: GraalVM's resource-config schema (v1.1.0) requires a top-level object, and `ResourceConfigurationParser` (graal release/graal-vm/23.1) rejects a non-object document, while `reflect-config.json` `[]` is valid. The owner's decision rested on an unverified format assumption, the tasks were removed after research, and the operator chose to ship nothing for `git-worktrees` (see lesson `2026-11-20-07-005` on amending the outline when a deliverable is dropped).

## Candidate rule

An outline never points at a question it has not recorded. A decision about the content of an external-format file (GraalVM metadata, a manifest, a schema-bound config) is checked against that format's schema or parser source before it is put to the owner as a recommendation and before it is frozen into the outline, because a wrong decision costs an infeasible execute dispatch, removed tasks and an unamended outline.
