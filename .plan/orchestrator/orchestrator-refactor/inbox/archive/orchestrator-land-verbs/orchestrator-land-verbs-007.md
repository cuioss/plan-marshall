envelope_version=1
sender_type=plan
sender_id=orchestrator-land-verbs
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-03T17:43:09Z

component=plan-marshall:manage-references
category=bug

# Sync affected_files when an operator adds a unit of work mid-execute

## Context

During TASK-1 of orchestrator-land-verbs the operator widened scope ("this must be done while establishing the worktree ... fix it now"), and a seventh unit of work — the `worktree_setup_commands` seam, TASK-12/13 — was added to the plan. It never received an outline heading or a references update. Nine realized paths ended up undeclared: six deliverable-7 files (`.plan/marshal.json`, `marshal-json-reference.md`, `_config_defaults.py`, `data-model.md`, `prepare_execute.py`, `test_prepare_execute_worktree_setup.py`), two shared test fixture modules and `uv.lock`. The metrics denominator still reads 6 deliverables.

## Root cause

Adding tasks for new scope during execute has no step that re-derives the declared footprint, so `affected_files` and the outline freeze at their 4-plan state while the realized footprint grows.

## Proposed action

Recurrence of active lesson 2026-09-29-17-002 — merge into it. Add the case: when execute appends tasks for operator-approved new scope, append a deliverable to the outline (or record the scope addition) and re-sync `affected_files` before the next commit.

## Evidence

- aspect: artifact_consistency — references_only 9, outline_only 0
- aspect: manifest_decisions — rule M6 declared_vs_realized_set fail, 9 realized-but-undeclared
- aspect: outline_vs_shipped — touched_but_unassessed 9 of 43
- aspect: request_result_alignment — 9 scope-creep files, 6 of them the unplanned deliverable 7
