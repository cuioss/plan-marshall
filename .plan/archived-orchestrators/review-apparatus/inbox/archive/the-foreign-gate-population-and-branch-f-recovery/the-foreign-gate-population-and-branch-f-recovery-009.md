envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=finding
created=2026-09-13T08:52:11Z

# `ci --plan-id … pr view` reports `auth_failed` after worktree removal, while gh is authenticated

Finding `2343b2` — `plan-marshall:tools-integration-ci`, severity `error`, resolved `accepted`
(carry-forward from plan `the-foreign-gate-population-and-branch-f-recovery`, PR #1473, merged
`38af136ed`).

## What was observed

Live, during that plan's own finalize, at `output-template.md` Snapshot Procedure step 4 — i.e. on
the renderer's own path, after `branch-cleanup` removed the worktree:

```
ci --plan-id the-foreign-gate-population-and-branch-f-recovery pr view
  -> status: error
     error: Not authenticated. Run 'gh auth login' first.
     error_cause: auth_failed
```

Identical envelope with `--pr-number 1473`. At the same moment:

- `ci_health verify` reported `gh installed: true, authenticated: true, version 2.98.0`;
- the same read through `--plan-id NO_PLAN` returned `status: success, state: merged, pr_number: 1473`.

So gh was authenticated throughout. The real condition is a worktree-resolution failure —
`metadata.use_worktree` is still `true` and `metadata.worktree_path` still names the directory
`branch-cleanup` deleted — mis-reported as an auth failure.

## Why it matters

**It is wrong in the most expensive direction.** `output-template.md` routes `auth_failed` into the
UNANSWERED arm → `state = unread` → Emission Procedure step 1 item 1 → `[FAILED]` headline. Every
worktree plan whose renderer makes this call post-`branch-cleanup` would render `[FAILED]` over a
cleanly merged PR. The arm exists to prevent a false green; here it manufactures a false red.

**It contradicts the documented resolver contract.** `tools-integration-ci/SKILL.md` states that a
worktree-state query that cannot be answered raises `WorktreeResolutionError`, and that the router
emits a structured TOON error and exits 2 — it explicitly does NOT degrade. Here it degraded into a
different error class entirely, which is worse than the refusal the contract promises.

## Remedy direction

Two faces of one root, and they should be judged together:

- The router must report a resolution failure as itself (`worktree_unresolved` /
  `WorktreeResolutionError`) rather than letting a downstream `gh` call fail and be classified as
  `auth_failed`.
- `branch-cleanup` / `worktree-remove` should clear `metadata.use_worktree` and
  `metadata.worktree_path` when it removes the worktree — this is the already-recorded `bd825d`
  defect (stale metadata blocking archive), same root.

Fixing only the `error_cause` classification leaves the resolver still failing on a path that no
longer exists.

## Containment on the originating run

The renderer's snapshot took the PR state through `--plan-id NO_PLAN`, which returned `merged` from
the provider, so that plan's final output rests on a genuine read rather than on the degraded arm.
