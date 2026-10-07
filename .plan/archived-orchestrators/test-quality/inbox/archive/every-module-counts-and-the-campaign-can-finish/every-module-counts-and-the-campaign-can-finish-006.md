envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:22Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Do not hand check-manifest-consistency a post-merge base-ref without a caveat

## Context

The manifest-decisions aspect reported a `fail` on this plan: "phase_6.steps includes branch-cleanup but the observed diff is empty — the footprint resolved to no changed path at all, so no implementation file changed", with `diff.files_total: 0`. The plan actually shipped 521 realized paths, and the two sibling aspects that resolve the footprint through the shared resolver both measured it correctly. The finding is a false positive.

## Root cause

Ordering. In the composed manifest, `branch-cleanup` is step 13 of phase_6 and `plan-marshall:plan-retrospective` is step 17 — the PR has already merged by the time the retrospective runs. `check-manifest-consistency` obtains its diff from `--base-ref`, and after the merge `origin/main` CONTAINS the plan's own changes, so `HEAD..origin/main` is legitimately empty. The SKILL.md canonical block says "Supply `--base-ref` whenever `--diff-file` is absent — it is how the script obtains a diff at all", with no post-merge caveat, so following the documented guidance produces a confident wrong answer on every plan whose finalize includes branch-cleanup ahead of the retrospective.

## Proposed action

Either (a) have the SKILL.md step pass the shared-resolver footprint as `--diff-file` rather than a `--base-ref`, which is what the other two footprint-consuming aspects already do, or (b) add a post-merge caveat to the canonical block and have the script report `base: merged_or_unknown` / `indeterminate` when the supplied base-ref contains HEAD. Option (a) is preferable and also satisfies the separate proposal to resolve the footprint once per finalize run.

## Evidence

- aspect: manifest_decisions — checks.branch_cleanup_changes `fail`; findings[1] `branch_cleanup_without_changes`; diff.files_total 0 with `diff_available: true` and `oracle_available: true`, so the emptiness was measured rather than unresolved
- aspect: outline_vs_shipped — footprint_source `resolved`, footprint_path_count 521, on the same tree
- aspect: routing_decisions — footprint_source `resolved`, same run
- manifest phase_6.steps ordering: branch-cleanup at index 13, plan-marshall:plan-retrospective at index 17
