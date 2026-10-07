envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T07:37:45Z

component=project:finalize-step-deploy-target
category=bug
created=2026-08-25

# deploy-target and sync-plugin-cache can run against a main checkout one commit behind the merge

## Context

Both project-local finalize steps document themselves as running "on the main checkout post-merge" so
the cache is re-derived "from the same authoritative merged source tree the dispatcher just wrote to".
Measured live on this plan: after the merge queue landed PR #1343 as origin/main `1169fb5bf`, the local
main checkout was still at `dfabe3d8e` -- one commit behind, missing the plan's own merged changes.
deploy-target's generator therefore emitted `target/claude/` from a tree WITHOUT this plan's content
(1176 entries, version 0.1.1543), and sync-plugin-cache mirrored that stale tree into
`~/.claude/plugins/cache/plan-marshall` for all 11 bundles, both steps reporting success.

## Root cause

Nothing in the phase-6 sequence pulls the local main checkout after the merge queue lands a PR: the
merge exists only on `origin/main` (branch-cleanup merges via the platform's merge queue), and
`integrate_into_main` moves the plan directory without touching the base branch. The staleness guard
that exists does not catch this because it fingerprints `marketplace/bundles/` in the WORKING TREE and
compares against a sentinel deploy-target itself just wrote from that same working tree -- the two
agree with each other while both disagree with the merged remote. The guard proves emit-vs-sync
consistency, never emit-vs-merge currency.

## Proposed action

Have deploy-target assert that local HEAD equals the merge commit branch-cleanup recorded (or pull)
before generating. The data needed is already available since branch-cleanup records the merge SHA.

## Evidence

- Finding 0c4569 in this plan's qgate store, detected only because a later step required
  `--head-at-completion` and the resolved SHA did not match the merge; corrected in-run by
  switch-and-pull (dfabe3d8e -> 1169fb5bf) and re-running both steps
- aspect: invariant_summary -- main_sha drift observed twice across this plan's own phase transitions
  (2-refine -> 3-outline, 4-plan -> 5-execute), the same class of staleness one level up
