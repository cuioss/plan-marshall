envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:26Z

component=plan-marshall:manage-solution-outline
category=improvement
title=manage-solution-outline: mark a deliverable de-scoped, with its tasks and paths, when an operator decision drops it after 3-outline
source_lesson=2026-11-20-07-005
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# manage-solution-outline: mark a deliverable de-scoped, with its tasks and paths, when an operator decision drops it after 3-outline

# Candidate lesson: dropping a deliverable mid-execute leaves the solution outline listing it as live scope

- Source signal: plan implement-plan-06-build-guards (inbox implement-plan-06-build-guards-012), plan-retrospective (artifact-consistency, manifest-decisions, logging-gap-analysis, request-result-alignment), component `plan-marshall:manage-solution-outline` and `plan-marshall:plan-marshall`, confidence high.
- Evidence: `task_deliverable_match` fails ("Deliverables without matching task: [7]"); 3 `outline_only` paths; `declared_vs_realized_set_mismatch` (3 declared-but-unrealized, 1 realized-but-undeclared); the work log carries only the two `manage-tasks remove` lines at 2026-11-20T06:33.

## What happened

In 5-execute, TASK-8 found that the decided empty-array `resource-config.json` for `git-worktrees` is invalid under GraalVM's schema. After research the operator chose "Ship nothing" and the orchestrator removed TASK-008 and TASK-009 with `manage-tasks remove`. `solution_outline.md` was never amended: deliverable 7, its three declared files and the Summary sentence "git-worktrees ships the same files with empty arrays" still read as live scope, and the frozen criteria still expect the folder.

## Root cause

Dropping a deliverable is done by removing its tasks. No step or verb marks the deliverable de-scoped in the outline and in `references.json`, and no decision line is required.

## Candidate rule

When an operator decision drops a deliverable after 3-outline, mark it de-scoped in `solution_outline.md` with the reason (or provide a `manage-solution-outline` verb that does so and removes its tasks in one call), drop its paths from `references.json`, amend the frozen criteria through the sanctioned re-freeze, and log a `[DECISION]` line.
