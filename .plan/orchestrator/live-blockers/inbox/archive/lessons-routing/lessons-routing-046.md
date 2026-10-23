envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:22:51Z

# A history rewrite invalidates the change ledger; the guarded 5-execute -> 6-finalize transition refuses

Severity: high. Bundle: **plan-marshall** (`manage-change-ledger`, `manage-status` transition gate, phase-5-execute, phase-6-finalize sync-baseline, `review_support`). Filed under RULING 2026-10-09 (a).

Recurrence across at least four plans (`plan-14`, `plan-37`, `plan-70`, `plan-91`, `plan-69`).

## Sources

- inbox `pm-mcp-core-m2-m4-307`, `-344`, `-345`, `-350`, `-366`, `-380`, `-396`

## Consolidated statement

The change ledger is pure-append and keyed by commit sha (`worktree_sha`). Every history rewrite — the default `sync-baseline` rebase, an amend, a cherry-pick — rewrites the branch's shas, so every previously recorded `kind=change` row stops matching the commit it describes.

Observed consequences:

- `manage-status transition --completed 5-execute` refuses with `execute_commits_unrecorded`, and because the rewrite is total the unrecorded count is the whole branch, not a stray commit (14 of 14, 8 of 11, 2 of 11 observed). The refusal names a single-commit bookkeeping gap while the real cause is that all prior rows are stale.
- Recovery is manual and unbounded: 10 re-appends after one rebase, 27 after the second; another plan re-recorded 11 commits by hand. `manage-change-ledger append` declares no `--plan-id`, so even the recovery has an argparse trap.
- Task commits cited in `work/coverage.md` and the decision log go stale after the rebase, and both functional-review rounds report them as false self-reports; nothing maps old sha to new.
- `review_support validate` cannot compute its delta round because the recorded delta base is no longer an ancestor of HEAD, so the dispatcher falls back to a full round as a workaround.
- `review_support attribution` can no longer match ledger rows to branch commits, degrades to `declared_only`, and lists legitimately changed files as unrequested.

## What is asked

- Add a remap / rebase-sync verb to `manage-change-ledger` that maps rows of rewritten commits onto their rebased counterparts (patch-id / `git range-diff`), keeping the ledger append-only by appending mapped rows; call it automatically after any history rewrite.
- Make the task-commit path append the ledger row in the same step as the commit, so a commit can never exist without its row; and have the refusal payload carry the exact unrecorded shas plus the ready-to-run append invocation for each.
- Have `finalize-step-sync-baseline` emit an old->new sha map whenever it rewrites commits, and correct or flag plan artifacts that cite the old ids.
- Treat an `execute_commits_unrecorded` refusal whose unrecorded set is the whole branch as the rewrite signature it is, not as a missed bookkeeping step.
- Let `review_support` switch explicitly to a full round when the delta base was rewritten, reporting `delta_base_rewritten: true`; share the same remap mechanism.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
