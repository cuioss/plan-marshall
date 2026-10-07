envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:22:22Z

component=project:finalize-step-lessons-housekeeping
category=bug

# Replace the retired modified_files read in lessons-housekeeping Step 1

## Context

Step 1 of .claude/skills/finalize-step-lessons-housekeeping/SKILL.md prescribes `manage-references get --field modified_files` to obtain the changed-file list. That field is retired: the call returns error: field_retired. In this plan the step ran six times, and each leaf improvised a replacement, trying `get --field realized_footprint` (field_not_found) and `compute-footprint --help` before landing on `manage-references compute-footprint --plan-id ... --worktree-path ...`, which returned the 149 changed files.

## Root cause

The project-local step doc was not updated when modified_files was retired in favour of the footprint verbs, so every firing breaks the no-improvisation rule just to get its input.

## Proposed action

Rewrite Step 1 to call `manage-references compute-footprint` (quoting its canonical invocation), and add the doc to whatever sweep guards retired manage-references fields.

## Evidence

- aspect: chat_history_analysis - lessons-housekeeping envelopes: "Stale Step 1 command: manage-references get --field modified_files returns error: field_retired"; "the get --field modified_files call in Step 1 is retired, so I used compute-footprint instead"
- status.json: project:finalize-step-lessons-housekeeping firing_count 6
