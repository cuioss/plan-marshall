envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:02:09Z

# Check canonical-forms table before inventing manage-* flags

## Context

Plan-02-worktree-discipline hit three paraphrase rejections: `get-deliverable --number` (declared `deliverable-number`), `manage-tasks update --task` (declared `task-number`), and retrospective `run --output` (no such flag). Each cost a retry; none blocked the plan.

## Root cause

Plausible flag names were extrapolated from workflow prose instead of quoted verbatim from the script argparse declaration.

## Proposed action

Route every new manage-* invocation through the persona canonical-forms table or `--help` first; keep the invented-verb drift entries current.

## Evidence

- aspect: script_failure_analysis — 3 argparse_other paraphrase rejections across manage-solution-outline, manage-tasks, plan-retrospective
