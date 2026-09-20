# WS-07: Merge-Coordination Hardening

epic: plan-optimization

> Charter document for one workstream. Tracked in the epic `status.json` `workstreams[]` field.

## Charter

Harden the merge-lock / FIFO merge-coordination layer so stale holders are actually reclaimed. Two
independent incidents this epic (PLAN-05, PLAN-08) had a merge blocked by a stale lock that the
existing `holder_is_dead` reclaim did NOT clear. Closes when a stale holder (vanished plan dir,
post-migration holder) is auto-reclaimed without manual release-under-holder-id.

## Scope

- In scope: `manage-locks` `_locks_core.holder_is_dead`, `merge_lock.py`, `build_queue.py` reap path
  — why the liveness predicate missed the two observed stale-holder classes.
- Out of scope: the ci merge-queue provisioning (WS-03, shipped); the build server itself (plan-server epic).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-15-stale-merge-lock-reclaim | staged | Fix `holder_is_dead`/reap so vanished-plan + post-#933-migration holders are reclaimed |

## Sequencing and Surface Notes

- Disjoint from everything in flight (PLAN-10/11/12) and the other new plans. Startable anytime.
