envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T12:59:58Z

# Fall back check-artifact-consistency footprint to the merge diff

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: wrong-store-guard-refuses-project-local-lessons

## Context

`check-artifact-consistency`'s live-mode footprint derivation is documented as: derive live from the
worktree (`{base}...HEAD` ∪ porcelain) when one is on disk, falling back to the legacy
`references.modified_files` key only for archived plans created before the ledger was removed. This
plan's own manifest orders `branch-cleanup` (which removes the worktree) BEFORE
`plan-marshall:plan-retrospective` in `phase_6.steps` — so a live, non-archived plan can legitimately
reach the retrospective step with its worktree already gone. When that happens, `check-artifact-consistency`
hits neither the worktree-diff path (no worktree) nor the legacy-key fallback (not archived), and silently
reports 0% recall against 6 declared-but-"missing" files.

## Root cause

The footprint derivation has a documented fallback for exactly one absent-worktree case (archived plans)
but not for the other legitimate absent-worktree case that this plan's own step ordering already produces:
a live plan retrospective running after its own worktree removal.

## Proposed action

Add a second fallback branch to the live-mode footprint derivation: when no worktree is present AND the
plan is not archived, derive the footprint from the merge/landing commit diff (resolvable via the plan's
`pr_number` / recorded `head_at_completion` shas in `status.metadata.phase_steps`), rather than reporting
an empty footprint.

## Evidence

- aspect: artifact-consistency — "Recall 0% below 70% threshold" with 6 files listed as "missing" that
  `git show a7a657b00` (the actual PR #1050 merge commit) confirms 4 of them WERE the exact touched files.
- aspect: request-result-alignment — cross-checked the same footprint manually against the merge commit
  and found 100% recall (4/4 declared write-files matched exactly, 0 scope creep).
