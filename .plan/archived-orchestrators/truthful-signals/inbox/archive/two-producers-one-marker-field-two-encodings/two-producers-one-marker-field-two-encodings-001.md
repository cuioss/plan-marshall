envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T04:54:28Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
suggested_epic=truthful-signals

# direct-gh-glab Surface B scans an empty post-merge diff and reports zero leaks

## Context

The `direct-gh-glab-usage` aspect scans two surfaces: (A) the plan's log files, and
(B) `git diff {base}...HEAD` added lines, for direct `gh`/`glab` invocations the CI
abstraction should have carried. For this plan it reported `counts.total: 0`,
`by_surface.diff_leak: 0`, `findings[0]` — a clean result.

Surface B scanned nothing. `plan-retrospective` runs as a phase-6 finalize step
positioned AFTER `branch-cleanup`, which merges the PR and removes the worktree. By
the time the aspect runs, the plan's commits are already in `main` and the cwd is the
main checkout, so `git diff main...HEAD` is empty. Verified directly for this plan:
`git diff --stat main...HEAD` returns nothing, while the plan's real 5-file footprint
is recoverable from the squash commit `cf70cf787`.

This is not a one-off. The step ordering that produces it is the normal finalize
order, so Surface B has reported a clean scan over an empty diff on every post-merge
retrospective.

## Root cause

Two independent collapses, both in `direct-gh-glab-usage.py`:

1. `_git_diff_added_lines` (lines 151-162) returns `[]` on `FileNotFoundError`, on
   `TimeoutExpired`, AND on `proc.returncode != 0`. A git failure and a genuinely
   empty diff are the same value to the caller.
2. `cmd_run` reports `counts.by_surface.diff_leak` with no denominator — no
   `files_scanned`, no `diff_lines_considered`, no `base_resolved`. A zero is
   therefore indistinguishable from "the diff had 500 lines and none leaked",
   "git failed", and "the diff was empty".

The aspect has no way to say *could not look*, so it says *clean*.

## Proposed action

- Emit the scanned denominator alongside the count: at minimum `base_ref`,
  `diff_files_considered`, and `diff_lines_considered`. A `diff_leak: 0` beside
  `diff_lines_considered: 0` is self-evidently a non-observation.
- Separate the git-failure path from the empty-diff path. A non-zero `returncode`
  or a missing binary should surface a distinct `surface_b_status:
  unavailable` rather than sharing the empty-list return.
- Resolve the post-merge footprint from the merge/squash commit when the worktree is
  gone and `status.metadata` carries a merged PR, rather than diffing against a base
  that has already absorbed the work. The same fallback fixes
  `check-artifact-consistency`'s `affected_files_exact_match: inconclusive`, which
  failed on this plan for the identical reason and whose answer was likewise one
  `git show --name-only` away.

## Evidence

- aspect: direct_gh_glab_usage — `counts.total: 0`, `by_surface.diff_leak: 0`,
  `findings[0]`, produced against an empty diff
- first-party: `git diff --stat main...HEAD` in the main checkout returns no output
- first-party: `git show --pretty=format: --name-only cf70cf787` returns the plan's
  actual 5-file footprint
- source: `direct-gh-glab-usage.py:151-162` (`_git_diff_added_lines` shared empty
  return), `:222-236` (`cmd_run` counts block with no denominator)
- ordering: `status.metadata.phase_steps["6-finalize"]` records `branch-cleanup`
  outcome `done` ("PR #1125 merged via merge queue, branch and worktree removed")
  before this step ran
- aspect: artifact_consistency — `affected_files_exact_match: inconclusive`,
  "Plan footprint could not be resolved (no live worktree diff and no modified_files
  key) — the comparison substantiates no verdict"
