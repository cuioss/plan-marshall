envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:56:58Z

component=finalize-step-lessons-housekeeping
category=bug
source_plan=lb-22-finalize-loop-control
confidence=high

# Replace the retired modified_files read in lessons-housekeeping with compute-footprint

## Context

The project-local step document `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` opens its Step 1 with `manage-references get --plan-id {plan_id} --field modified_files`. That call returns `status: error, error: field_retired`; the error message itself points at `compute-footprint` and `references.realized_footprint`.

The step fired 7 times in this plan and hit the error every time. Four firings made no substitute call and classified the lessons corpus on the request document plus whatever the dispatcher happened to describe; three firings used `manage-references compute-footprint --plan-id ... --worktree-path ...` (53 to 54 files). The step's classification input therefore differed between firings of the same step on the same plan.

## Root cause

The field was retired in `manage-references` without updating this step document. The document lives under `.claude/`, which the architecture content search does not walk, so a sweep for callers of the retired field did not find it.

## Proposed action

- Replace the Step 1 call with the `compute-footprint` invocation and rename the `modified_files` mentions in the HEAD-dependency section, the verdict-input section and the "Missing quality-verification-report.md" error row.
- When a field or verb is retired, include `.claude/skills/**` in the caller sweep explicitly.

## Evidence

- source: lines 101-102 of `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` at main `6b00815e0` still carry the retired call; `modified_files` is also named at lines 55, 65, 110 and 330.
- aspect: chat_history_analysis - all seven lessons-housekeeping hand-backs report `field_retired`.
- aspect: log_analysis - work-log entry at 2026-10-08T18:14:58Z: "classified on request.md plus the compute-footprint file list (manage-references get --field modified_files is retired)".
