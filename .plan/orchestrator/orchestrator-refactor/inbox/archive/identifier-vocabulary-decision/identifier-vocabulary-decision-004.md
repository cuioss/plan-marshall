envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:24:50Z

component=plan-marshall:manage-references
category=bug
title=Reconcile realized_footprint against the merge commit before it is recorded

# Reconcile realized_footprint against the merge commit before it is recorded

## Context

`references.json` records a `realized_footprint` of three paths: the ADR, `argument-naming.md`, and `uv.lock`. The merge commit the plan actually landed, `4804b6976` (PR #1543), contains only the first two. `uv.lock`'s most recent commit is `a1dd4901f` — PR #1541, the immediately preceding landing — and `uv.lock` is clean in the working tree.

The sequence that produced this: a dependabot re-lock left `uv.lock` dirty in the worktree; the operator was asked how to handle a dirty file mapping to no deliverable and answered "Absorb into this PR"; the footprint was then captured from worktree git state with `uv.lock` included; `finalize-step-sync-baseline` later rebased onto `origin/main`, picking up 2 upstream commits — one of which already carried the identical re-lock — so the plan's own copy of the change collapsed to a no-op and never entered the merge commit.

The operator's intent was satisfied (the re-lock is on main) but not by this plan, and the plan's record of what it shipped over-claims by one file.

## Root cause

The realized footprint is captured from pre-rebase worktree state and is never re-derived against the merge commit, so any change the rebase collapses to a no-op remains recorded as shipped.

## Proposed action

Re-derive or verify `realized_footprint` against the merge commit once `merge_commit_sha` is known — both values are already recorded side by side in `references.json` — and report the delta rather than letting the pre-rebase capture stand as the record.

## Evidence

- aspect: request_result_alignment — `references_json_realized_footprint` 3 paths vs `merge_commit_paths` 2; `over_claimed: [uv.lock]`
- aspect: artifact_consistency — `affected_files_exact_match` reports `references_only: [uv.lock]`
- `git diff --name-only a1dd4901f 4804b6976` yields exactly 2 paths, both documentation
- `git log -- uv.lock` places its latest change at `a1dd4901f` (#1541), not `4804b6976` (#1543)
