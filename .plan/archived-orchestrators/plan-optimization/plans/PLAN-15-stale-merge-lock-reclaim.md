# PLAN-15: stale-merge-lock-reclaim

epic: plan-optimization
workstream: WS-07

> Staged plan spec. Promoted from the stale-merge-lock watch (n=2: PLAN-05 #931, PLAN-08 #934).
> Orchestrator-verified 2026-07-18: the reclaim mechanism EXISTS but missed both holders. Re-ground
> citations at outline.

## Objective

Make stale merge-lock holders actually auto-reclaimed, so a merge is not blocked behind a dead
holder that manual `release-under-holder-id` had to clear. The `manage-locks` liveness predicate
`_locks_core.holder_is_dead` and the `merge_lock.py` / `build_queue.py` reap paths already exist —
but two distinct stale-holder classes slipped through this epic: (PLAN-05) a lock held by a VANISHED
plan directory (the original ci-pr-safe-merge dir that never persisted), and (PLAN-08) a lock left by
the merge-group-guard plan after `#933` moved `merge_lock` into `manage-locks`. So this is a coverage
bug in an existing predicate, not a new mechanism.

## Deliverables

### D1 — `holder_is_dead` / reap must recognize the two observed stale-holder classes

**Verified (orchestrator, 2026-07-18):** `manage-locks` has `_locks_core.holder_is_dead` (liveness
predicate keyed on the worktree/plan dir) + a `reaped-stale` / dead-holder prune in `build_queue.py`
and `merge_lock.py`. Both incidents held a lock the reap did NOT clear. **Fix:** make the predicate
correctly judge (a) a holder whose plan dir vanished entirely (no worktree, no plan → dead) and
(b) a holder stranded by the `#933` merge_lock→manage-locks migration. **Acceptance:** a merge-lock
held by a vanished-plan holder and by a post-migration holder is auto-reclaimed on the next
acquire/reap attempt without manual release; a genuinely-live holder is NOT reclaimed (no false
reclaim). Regression tests for both stale classes + the live-holder negative.

## Out of scope / do NOT expand
- The ci merge-queue provisioning (WS-03, shipped).
- The build server / marshalld (plan-server epic).

## Absorbs
- The stale-merge-lock watch (PLAN-05 + PLAN-08 incidents).

## Expected Surface
- `manage-locks/scripts/_locks_core.py` (`holder_is_dead`), `merge_lock.py`, `build_queue.py` (reap)
- tests: vanished-holder reclaim, post-migration-holder reclaim, live-holder no-false-reclaim

## Dependencies and Sequencing
- Depends on: none. Disjoint from everything in flight and the other new plans.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-15-stale-merge-lock-reclaim.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-15.md is recorded}
