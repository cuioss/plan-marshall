envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-30T06:51:30Z

# Freshness gate goes stale after reverting formatter churn that a `verify -Ppre-commit` gate wrote

**Component:** `plan-marshall:manage-change-ledger` / `manage-tasks pre-commit-verify-freshness` and the `pre-push-quality-gate` finalize step.

**What happened (API-Sheriff PR #537, plan `plan-v02-07-threat-classification`).** In a Maven project the `quality-gate` canonical (`verify -Ppre-commit`) is `mutating: true`: it rewrites hundreds of tracked files (import blank-line / continuation-indent churn in files the branch did not author). The `kind=build` ledger row is stamped with the **post-rewrite** tree hash. The repository's rule is to revert that churn (`git checkout -- .`), which restores the original tree whose hash no row carries, so `pre-commit-verify-freshness` returned `stale` / `worktree_mutated` even though every gate was green. The only way out was to run an additional non-mutating build (`test -pl ... -am`, ~7 min) on the clean tree purely to mint a matching row.

**Why it matters.** Every plan on a repo with a mutating quality gate pays this extra build at both the phase-5 exit and the push precondition, and the gate message ("worktree has been mutated since the last observed build") points at a mutation that was already undone.

**Suggested fix.** Stamp the build row with the pre-gate tree hash for a `mutating` canonical (or record both), or allow the freshness gate to accept a row whose rewrite was reverted to the pre-build tree.
