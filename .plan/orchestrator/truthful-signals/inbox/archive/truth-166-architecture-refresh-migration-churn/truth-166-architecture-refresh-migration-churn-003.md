envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:14Z

component=plan-marshall:manage-references
category=bug
confidence=high
rank=3
source_plan=truth-166-architecture-refresh-migration-churn

# Resolve compute-footprint base_ref to the remote-tracking ref, not the bare local branch

## Context

`resolve_base_ref` falls back to `references.base_branch`, which is the bare LOCAL branch
name (`main` on this plan). `compute_plan_branch_diff` then runs a three-dot
`main...HEAD` diff, and its docstring asserts:

    The three-dot form excludes files that arrived on the branch from base_ref via an
    absorb merge, so the footprint reflects only files the plan branch actually touched.

That guarantee holds only while the local branch is level with the remote. After
`finalize-step-sync-baseline` rebases the worktree onto `origin/main`, local `main` is an
ANCESTOR of HEAD, so the merge base is local `main`'s tip and every upstream commit
between local `main` and `origin/main` lands on the HEAD side of the diff — attributed to
the plan.

## Root cause

The base ref names a local pointer that the finalize workflow itself outruns.
`branch-cleanup` is what advances local `main` (it pulls), and it runs near the END of
finalize — so for the whole middle of the phase, local `main` is stale while the worktree
has already absorbed upstream commits. The three-dot form is chosen precisely to exclude
absorbed upstream files, and it fails to do so because it is anchored to the wrong ref.

## Proposed action

Resolve `base_ref` to `origin/{base_branch}` (the remote-tracking ref), or to the ref
`finalize-step-sync-baseline` actually rebased onto, which that step already knows. Then
correct `compute_plan_branch_diff`'s docstring, whose current guarantee is stated without
the staleness precondition it depends on.

## Evidence

- source: `manage-references/scripts/_references_core.py:171-176` — `base_branch =
  refs.get('base_branch')`, returned verbatim; final fallback is the literal `'main'`.
- source: `_references_core.py:241` — `diff --name-only {base_ref}...HEAD`.
- This plan recorded 3 upstream commits at branch-cleanup
  (`upstream_commit_count: "3"`), while `references.base_branch` remained `main`.
- The shipped consequence is recorded in the plan's own PR body: "The finalize simplify
  pass proposed three dead-branch removals in files that arrived from upstream `main`
  and lie outside this plan's declared surface." All three were reverted — caught by
  review, not by the footprint.

## Generalizes

A confident docstring guarantee is at its most dangerous when it is void in exactly the
situation the surrounding workflow creates. Here the workflow's own rebase step is what
invalidates the claim, so the guarantee fails on the standard path rather than an edge
case — and a downstream step (simplify) acted on the contaminated set.
