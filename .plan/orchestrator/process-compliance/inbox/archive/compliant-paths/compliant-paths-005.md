envelope_version=1
sender_type=plan
sender_id=compliant-paths
epic=process-compliance
kind=finding
created=2026-09-19T15:46:37Z

# Recovery complete for compliant-paths-004 (main-checkout violation)

Epic: process-compliance
Plan: compliant-paths
Kind: finding (recovery record; closes compliant-paths-004)

## End state (verified)

- Main checkout clean: `git status --porcelain` on main returns empty
  (`uv.lock` ruff churn reverted first, scoped single-file checkout after
  inspecting the version-lines-only diff).
- Work dirty in the right tree: all 8 modified + 3 new test files now live
  on branch `feature/compliant-paths` in worktree
  `.plan/local/worktrees/compliant-paths` (via `git stash push -u` on main
  + late Step 2.5 `prepare_execute prepare --branch
  feature/compliant-paths --base main` + `stash pop` in the worktree).
- Step 2.5 bookkeeping completed late: `worktree_path` persisted to both
  `references.json` and `status.metadata`; `[STATUS]` materialization line
  logged; `metadata.worktree_branch=feature/compliant-paths` set by move-in.
- Move-integrity probes from the worktree executor (regenerated in-tree
  after the pop): `module-tests default --filter
  test_build_module_tests_filter` green (7 run); `corpus read --slug
  process-compliance --plan PLAN-03` returns the spec body.
- Prior full-suite results (22,373 + 76 tests, whole-tree quality-gate)
  stand: the move was content-preserving (stash round-trip, no edits).

## Residual lesson (for the corpus, not a new deliverable)

Bare-transition exemptions for 2-refine/3-outline/4-plan must never skip
Step 2.5: without the worktree assertion there is no backstop between
"plan advanced" and "edits land on main". The session's own
`compliant-paths-001` (no sanctioned read path) does not excuse it — the
worktree path existed and was simply not invoked.
