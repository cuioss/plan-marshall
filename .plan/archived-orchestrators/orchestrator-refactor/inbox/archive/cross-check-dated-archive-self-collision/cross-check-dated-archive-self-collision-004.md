envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:22Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Diff scope-creep and task artifacts against the merge base

## Context

While the plan was paused for a red main, the feature branch was fast-forwarded onto the repaired main. From then on two phase-5 measurements attributed upstream files to the plan:

- The scope-creep guard counted 6 and then 16 "residual" paths over its threshold of 5. Every one came from upstream commits #1665-#1668; the plan had edited only its declared files.
- Closing TASK-1 emitted 14 `[ARTIFACT]` lines, of which 10 name files the plan never touched (`doc/antigravity/*`, `doc/developer/*`, `doc/user/*`, `test/plan-marshall/manage-config/test_config_defaults.py`).

## Root cause

Both diffs run from a fixed commit recorded before the branch moved: `plan_creation_sha..HEAD` for the guard and `task_start_sha..HEAD` for the artifact lines. Once main is merged or fast-forwarded into the branch, those ranges contain upstream history, so everything upstream changed reads as the plan's or the task's work.

## Proposed action

Compute both ranges from the merge base with the base branch (the plan's own contribution), or re-stamp the recorded start commits whenever the baseline is reconciled. Add a test where upstream commits land between the recorded commit and HEAD and assert they are counted for neither the guard nor the artifact lines.

## Evidence

- decision.log 2026-10-01T07:36:34Z (6 paths, all from 0f94c0d8f and 638e13906), 10:01:38Z and 10:10:57Z (16 paths, HEAD equals origin/main 427649eb2)
- decision.log 2026-10-01T09:51:14Z (fast-forward 638e13906 to 427649eb2 with uncommitted plan files preserved)
- work.log 2026-10-01T10:03:38Z (TASK-1's 14 artifact lines)
- leaf hand-back for the second execute envelope: "TASK-1's [ARTIFACT] lines over-attribute"
