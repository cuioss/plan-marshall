envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:47:45Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
created=2026-07-29

# A stale local main silently widens the candidate diff — and silently seeds the branch

Two independent defects this run, both rooted in **local `main` being treated as a trustworthy
baseline** when it was behind `origin/main`. Both produced confident, well-formed output about the
wrong set of changes.

## Evidence

1. **The self-review surfacer defaults to `--base-branch main`** — the *local* ref. With local
   `main` behind `origin/main`, the diff `main...HEAD` included **already-merged upstream files**.
   The surfacer then examined and reported on code the plan never touched. Its verdict
   ("37 candidates examined, no check matched") was arithmetically about a population larger than
   the change, so the number reads as thoroughness while describing the wrong scope.

2. **An unpushed local-main commit was swept onto the feature branch at worktree creation.** The
   commit rode the branch invisibly. Only a **second** rebase — after the same change landed
   upstream independently as #1048 — dropped it. A single rebase was not sufficient, because the
   first one had nothing upstream to reconcile the commit against.

## Solution

- **Baseline against the remote, not the local ref.** Any diff-scoping default that names a branch
  must resolve to `origin/{branch}` (or fetch first), because a local tracking branch is a cache
  with no freshness guarantee. Change the surfacer's `--base-branch` default resolution
  accordingly — a fix at the tool layer, not a per-run habit.
- **Check local-main freshness before creating a worktree.** A local `main` carrying unpushed
  commits contaminates every branch cut from it. Detect and refuse (or report) at worktree-creation
  time, where it is one commit, rather than at rebase time, where it is indistinguishable from the
  plan's own work.
- **Treat a candidate-count as a scope statement, not a coverage statement.** "N candidates
  examined" says nothing about whether the N were the right N — the recurring
  volume-read-as-coverage archetype, here with an inflated denominator.

## Impact

Applies to the pre-submission self-review surfacer's default base resolution and to worktree
creation in `workflow-integration-git`. Both are one-line-class fixes at the tool layer that remove
an entire class of "reviewed the wrong diff" outcomes.
