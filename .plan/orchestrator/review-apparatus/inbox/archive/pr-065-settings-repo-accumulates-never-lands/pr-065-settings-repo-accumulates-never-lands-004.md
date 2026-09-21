envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:07:48Z

component=plan-marshall:manage-references
category=bug
confidence=high
source_plan=pr-065-settings-repo-accumulates-never-lands

# affected_files is never updated as execute discovers new files

## Context

`references.json` for this plan declares 19 `affected_files` and records a 13-path
`realized_footprint`. The two sets are not nested — five realized paths are absent from the
declared list, and four declared local paths were never modified:

Realized but never declared:

- `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_manage_invocation.py`
- `test/pm-plugin-development/plugin-doctor/test_analyze_manage_invocation.py`

Declared but never realized: `tools-integration-ci/scripts/ci_base.py`,
`workflow-integration-gitlab/scripts/gitlab_ops.py`, and their two test files.

The first two realized-but-undeclared paths are the targets of TASK-012 and TASK-013 — fix
tasks appended to deliverable 1 during execute. The task records name the files; the
declaration never absorbed them.

## Root cause

`affected_files` is written at outline time and is not re-derived when execute appends
fix-tasks or discovers new targets. The realized footprint is captured separately and
correctly, so the data to reconcile the two exists — nothing joins them.

## Proposed action

Have the fix-task append path (and any execute-time step that adds a task with a new
`steps[].target`) add that target to `affected_files`, or have `manage-references` expose
the existing three-way reconciliation as a gate at end-of-execute rather than as a
read-only comparison. Any finalize step that scopes itself from `affected_files` under-scoped
by five files on this plan, including two that a fix-task had explicitly named.

## Evidence

- aspect: artifact-consistency — `affected_files_exact_match,info,Set mismatch`; `references_only[5]`
- aspect: request-result-alignment — `scope_creep[5]`, two attributed to TASK-012/TASK-013, three unattributable
- source: `references.json` — `affected_files` 19 entries vs `realized_footprint` 13 entries, non-nested
