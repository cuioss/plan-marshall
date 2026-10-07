envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:16:46Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# Retrospective diff-derived checks return empty after branch-cleanup removes the worktree

## Context

On plan `self-review-cannot-see-an-unreachable-guard` (PR #1042, merged, 11 files changed), the
`artifact-consistency` aspect's `affected_files_recall` check reported `found: 0` against 10
declared files (recall 0%), and the `manifest-decisions` aspect's diff derivation reported
`diff.files_total: 0` with `base: unknown`. Both symptoms are identical: the live-diff derivation
these two script-backed checks rely on returned nothing.

## Root cause

`plan-marshall:plan-retrospective` is manifest-ordered AFTER `branch-cleanup` in
`phase_6.steps` (`...branch-cleanup, plan-marshall:plan-retrospective...`), and `branch-cleanup`
removes the plan's worktree once the PR merges. Both `check-artifact-consistency` and
`check-manifest-consistency` derive their footprint live from `{base}...HEAD` plus the porcelain
diff of a worktree that, by the time either script runs, no longer exists. The manifest-decisions
fragment's own facts confirm this (`base: unknown`, `files_total: 0`) rather than reporting a
genuine zero-file plan.

## Proposed action

Give both checks a fallback footprint source for the post-worktree-removal case: resolve the
plan's `metadata.worktree_sha` / `metadata.main_sha` (or the merged PR's commit range recorded at
`create-pr` / `branch-cleanup`) and diff against the main-checkout git history instead of the
now-absent worktree. This is the same finalize-ordering defect shape already fixed once for
`finalize-step-lessons-housekeeping` (`project_plan10_shipped_finalize_ordering_defect`) — a
component whose evidence source is destroyed by an earlier-ordered step in the same pipeline it
runs inside.

## Evidence

- aspect: artifact-consistency — `affected_files_recall: {declared: 11, found: 0, recall_pct: 0.0}`
- aspect: manifest-decisions — `diff: {base: unknown, files_total: 0, files_filtered: 0, files_kept: 0}`
- verified independently: `git show --stat 8e49ed0fa` (the squash-merge commit) shows 11 files
  changed, so the plan's real footprint is non-empty — the 0% recall is a detector artifact, not a
  real coverage gap.
