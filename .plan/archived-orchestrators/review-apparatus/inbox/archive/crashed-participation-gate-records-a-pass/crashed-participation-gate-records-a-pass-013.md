envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:37Z

# Emit a per-task [ARTIFACT] entry at task completion in phase-5-execute

component: plan-marshall:phase-5-execute
category: bug
confidence: high
source: plan-retrospective (aspect: logging-gap-analysis)
suggested_epic: truthful-signals

## Context

The plan completed 8 tasks, every one of which produced file changes, and emitted 8 matching `[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN` lines. It emitted ZERO `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` lines.

The 10 `[ARTIFACT]` entries in the run all come from other phases: request.md and plan creation (1-init), solution_outline.md created and updated (3-outline), TASK-1/2/3 created (4-plan), PR #1070 and review-retrospective.md (6-finalize).

## Root cause

`plan-retrospective/references/logging-gap-analysis.md` § ARTIFACT_EMISSION specifies: "every `[OUTCOME]` line emitted for a task that produced file changes MUST be immediately followed by at least one `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` line", and states the expectation as "one `[ARTIFACT]` entry per file operation at task completion". Phase-5-execute does not implement that emission.

Note the check's own escape hatch masked it: the ARTIFACT_EMISSION rule has an OLD branch (zero `[ARTIFACT]` entries anywhere with a non-empty footprint = error) and a NEW branch (per-task pairing). The old branch passes here because 10 `[ARTIFACT]` lines exist — they just all come from other phases. Only the phase-scoped new branch catches it. A whole-plan count is not a substitute for a phase-scoped one.

## Proposed action

1. Emit `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` at each task close, naming the files the task actually touched.
2. Make the check phase-scoped explicitly: count `[ARTIFACT]` entries whose component tag is `phase-5-execute:*`, not all `[ARTIFACT]` entries in the file. As written, a plan with plenty of phase-1/3/4 artifacts can never trip the old branch regardless of what phase-5 does.

## Evidence

- aspect: logging-gap-analysis — `ARTIFACT_EMISSION, expected_min 8, observed 0`
- `logs/work.log` — 8 `[OUTCOME] ... Completed TASK-001..TASK-008` lines (13:19:36, 13:54:36, 14:25:42, 16:20:53, 16:27:04, 16:33:19, 16:43:05, 16:45:05)
- aspect: log-analysis — `artifact_entries: 10`, `outcome_pairing.paired: 8` with zero unpaired
- the landed diff touched 10 files, so every one of those 8 tasks was file-changing
