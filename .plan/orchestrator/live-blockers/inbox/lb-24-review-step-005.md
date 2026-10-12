envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:58:06Z

component=finalize-step-lessons-housekeeping
category=bug

# Replace the retired modified_files read in lessons-housekeeping Step 1

## Context

The project-local step `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` Step 1 calls `manage-references get --field modified_files`. In plan lb-24-review-step that call returned `error: field_retired` on every one of the ten firings ("reads route through compute-footprint / references.realized_footprint"). Each dispatch improvised differently: some substituted `compute-footprint` (one first without the required `--worktree-path`, rejected with exit 2), some used `git diff --stat`, some classified on request.md alone. A subagent noted an earlier lesson on the same defect; that lesson was among those lost when the lessons corpus emptied mid-run, so it may need re-filing.

## Root cause

The step document still names a field the references store retired; nothing guards the document's invocations against the live argparse and field set.

## Proposed action

Replace the Step 1 read with `manage-references compute-footprint --plan-id {plan_id} --worktree-path {worktree_path}` (or the captured realized footprint after merge), and remove the em dash from the Step 2 display_detail templates while there.

## Evidence

- work.log 2026-10-09T15:24:10Z: compute-footprint rejected for missing --worktree-path
- housekeeping hand-backs at e1f579f0d, e2b8d0b45, 8fc4ed521 and c6571e103: field_retired on Step 1
- one housekeeping firing recorded mark-step-done twice because the template's em dash broke the ASCII rule
