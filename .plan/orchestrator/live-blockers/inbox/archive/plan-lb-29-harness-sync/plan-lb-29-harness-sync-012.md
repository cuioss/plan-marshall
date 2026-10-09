envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:40Z

component=project:finalize-step-lessons-housekeeping
category=bug
created=2026-10-09

# Replace the retired modified_files read in lessons-housekeeping Step 1

## Context

The lessons-housekeeping finalize step fired three times on plan `plan-lb-29-harness-sync`. Step 1 of its document (`.claude/skills/finalize-step-lessons-housekeeping/SKILL.md`) tells the step to read the plan's changed files with `manage-references get --field modified_files`. That read returns `error: field_retired`. On all three firings the step used `manage-references compute-footprint --plan-id ... --worktree-path ...` instead, with flags taken from `--help`, and disclosed the deviation each time.

This is a recurrence. The step's own third firing on this plan retained existing lesson `2026-10-08-21-001` with the note that it "hit the same condition" and that "the defect is unfixed".

## Root cause

The step document was not updated when the `modified_files` field was retired from `manage-references`. The document is project-local and outside the plan's changed files, so no plan that trips over it is in a position to fix it.

## Proposed action

- Replace the Step 1 command in the step document with the `compute-footprint` call, written out in full with its flags.
- Sweep the other project-local finalize steps under `.claude/skills/` for the same retired read. That tree is outside the inventory content search, so it needs a direct search.
- Consider having the `field_retired` error print the exact replacement call, so a step that still names the old read can recover without consulting help.

## Evidence

- aspect: chat_history_analysis — first firing: "Step 1's first command is broken. `manage-references get --field modified_files` returned `error: field_retired`"; second firing: "`manage-references get --field modified_files` was not called (retired); `compute-footprint` was used instead".
- decision log — da5fc2 (third firing): "retained 2026-10-08-21-001: this firing hit the same condition (Step 1 of the step document still names the retired modified_files read; compute-footprint used instead, 60 files) and the step document is not in the plan footprint, so the defect is unfixed".
- aspect: script_failure_analysis — one argparse rejection of `manage-references get` (exit 2) at 2026-10-08T12:52:01Z, earlier in the same plan, shows the same verb being reached for from another step.
