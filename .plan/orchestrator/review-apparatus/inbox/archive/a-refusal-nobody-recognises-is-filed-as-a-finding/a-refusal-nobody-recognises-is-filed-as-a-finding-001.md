envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:21:37Z

component=plan-marshall:phase-6-finalize
category=bug
title=branch-cleanup's merge-queue path leaves realized_footprint unwritten, so every post-merge footprint read is unresolvable

# branch-cleanup's merge-queue path leaves realized_footprint unwritten

## Context

`plan-retrospective` runs at order 995 — after `branch-cleanup` has removed the worktree. Its footprint resolver (`_footprint_resolver.resolve_footprint`) therefore has four tiers, and for this plan all four missed: `check-artifact-consistency` returned `affected_files_recall: inconclusive` and `affected_files_exact_match: inconclusive` with the message "no live worktree diff, no realized-footprint capture, no merge-commit, no modified_files key". Both of the retrospective's coverage checks — the deterministic half of the scope x thoroughness contract — produced no verdict at all.

## Root cause

`_footprint_resolver`'s own docstring states that `references.merge_commit_sha` (tier 3) "is recorded by `default:branch-cleanup` only on the synchronous merge path; on the async merge-queue path it is absent and tier 2 is the resolution." This plan merged via the queue (`merge_mechanism: merge_queue`), so tier 3 is absent by design. Tier 2 — `references.realized_footprint`, which branch-cleanup is supposed to capture via `manage-references capture-footprint` while the worktree still exists — was never written either. `references.json` for this plan carries only `branch`, `base_branch`, `scope_estimate`, `domains`, `track` and `affected_files`.

The design names tier 2 as the resolution for exactly the path that was taken, and the step that owns tier 2 did not write it. `branch-cleanup` nevertheless reported `outcome=done` with `work_performed=true`.

## Proposed action

Make `capture-footprint` unconditional on every branch-cleanup path that removes the worktree, and assert its presence before the removal. Alternatively, record `merge_commit_sha` on the merge-queue path too — the squash landing `dfabe3d8e` was on `main` and reachable at retrospective time, and tier 3's `{sha}^1..{sha}` range would have resolved the exact 19-file footprint.

## Evidence

- aspect: artifact_consistency — `footprint_resolved: false`, both coverage checks `inconclusive`
- `references.json` carries neither `realized_footprint` nor `merge_commit_sha`
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"]`: `merge_mechanism: merge_queue`, `work_performed: "true"`, `outcome: done`
- `git show --name-only dfabe3d8e` resolves 19 files — the footprint was recoverable, it was simply not recorded
