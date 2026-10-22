envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:31Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-10-21
bundle=plan-marshall

# A rebase invalidates every kind=change ledger row, so the 5-execute transition refuses

The change ledger records one `kind=change` row per worktree-branch commit, keyed by
`worktree_sha`. A sync-baseline rebase rewrites every commit SHA on the branch, so every
row appended before the rebase stops matching the commit it describes. The guarded
5-execute -> 6-finalize transition then refuses with `execute_commits_unrecorded`, and
because the rewrite is total the unrecorded count is the whole branch, not a stray
commit.

Observed in plan-91-plan-instance-advisories:

- 12:37:04Z the transition refused with 1 of 8 commits unrecorded (53c5aa1) before the
  rebase.
- 14:29:21Z finalize sync-baseline rebased onto origin/main (3 upstream commits).
- 17:25:25Z, after TASK-009's commit, the same transition refused with 8 of 11 commits
  unrecorded — the rebase had rewritten the 8 previously recorded ones.
- 17:30:29Z the loop-back note records the resolution: "11 commits each carry a
  kind=change row after the rebase rewrote their SHAs".

## Solution

Treat any history rewrite (sync-baseline rebase, amend, cherry-pick) as invalidating the
ledger wholesale. After the rebase, re-append one `kind=change` row per branch commit at
its NEW sha before the next guarded transition, and read an `execute_commits_unrecorded`
refusal whose unrecorded set is the whole branch as the signature of a rewrite rather
than of a missed bookkeeping step.

`manage-change-ledger append` declares no `--plan-id`; passing it is rejected with
`unrecognized arguments` (observed at 12:44:11Z). The store is cwd-resolved, so append
from the tree the ledger belongs to.

## Impact

Every plan that rebases during 6-finalize (the default sync-baseline step) and then
re-enters 5-execute for a loop-back. The refusal is correct but misleading: it names a
single-commit bookkeeping gap while the real cause is that all prior rows are stale.
