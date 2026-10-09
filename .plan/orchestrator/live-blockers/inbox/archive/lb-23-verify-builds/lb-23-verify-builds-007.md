envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:54Z

component=plan-marshall:plan-marshall
category=anti-pattern
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Pass WORKTREE as a repo-relative path in every execution-context dispatch

## Context

The execution-context contract says `WORKTREE` is a repo-relative path (or `.`), never absolute, and that the leaf uses it verbatim as the root of every file operation. On plan lb-23-verify-builds at least 8 hand-backs report it arriving as an absolute path, and three finalize dispatches after the merge (verification-feedback round 3, review-retrospective, and this plan-retrospective) received the literal `--plan-id lb-23-verify-builds` as its value. Every leaf worked around it and said so.

## Root cause

The orchestrator composes the field from whatever it has to hand: the absolute path `get-worktree-path` returns while the worktree exists, and a flag fragment once it is gone. The contract value for the post-merge main checkout is `.`.

## Proposed action

- Compose `WORKTREE` in one place in the orchestrator's dispatch seam: relativize the worktree path against the repository root, and emit `.` when the plan has no worktree (before materialization and after branch cleanup).
- Have the execution-context dispatcher reject a value that is absolute or starts with `--` in its Step 1 contract validation; today a malformed value passes because only presence is checked.

## Evidence

- aspect: chat_history_analysis - "WORKTREE arrived as an absolute path although the contract says repo-relative; I used it as given" (triage, plugin-doctor, self-review fix, automatic-review hand-backs); "WORKTREE was malformed. It arrived as --plan-id lb-23-verify-builds, which is not a path".
- This retrospective's own dispatch carried `WORKTREE: --plan-id lb-23-verify-builds`.
