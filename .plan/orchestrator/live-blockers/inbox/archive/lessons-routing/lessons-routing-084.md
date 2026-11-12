envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-10T16:59:37Z

# Merge gate does not prove the calling plan holds the merge mutex; a not-live holder blocks admission

**Severity:** high (operator grade, 2026-11-10 drain of the lessons-routing inbox)
**Bundle:** plan-marshall (`manage-locks`, `phase-6-finalize`)
**Checked at:** `e7033b83a` (origin/main)

## What was reported

Two messages from the pm-mcp-core plan `plan-v2-86-core-store-tests-b` (PR 301), both about the cross-plan merge mutex:

1. In branch-cleanup, `merge_lock acquire` returned `admission=blocked` (holder `plan-v2-89-runtime-tests-start-and-config`, liveness `not_live`) after a 240 s wait. The `ci pr merge-queue` enqueue still ran in the same shell call, so the plan merged WITHOUT holding the mutex. The sender's cause: an orchestrator procedure error, commands chained without reading the admission result. Its proposed fix: the merge gate refuses to enqueue unless it can prove the calling plan holds the lock.
2. The same holder had `liveness: not_live` and `location: not_found` in `merge_lock queue-list` (position 0, `lock_held: true`) yet still blocked the FIFO admission for the whole 240 s. Proposed: reclaim the lock, or promote the waiter, when the holder is not live and its location cannot be found.

## Ground truth at the checked commit

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` contains no reference to `merge_lock`, `holds_lock`, `lock_held` or an admission check on the lock. A grep for those terms matches only the unrelated "admission" wording at lines 197, 245 and 522. So item 1 is confirmed as far as reading shows: the gate has no lock-holder proof, and a chained enqueue is not refused.
- Item 2 (stale-holder reclaim) was NOT re-verified in `manage-locks` code; it rests on the sender's `queue-list` output.

## Relation to filed work

`lessons-routing-054` (high) filed the ownership side of the same lock: ownership keyed on `plan_id`, so a same-plan session can release another's lock. This is the enforcement side (the gate never asks) plus a liveness-reclaim gap. Please check both against `PLAN-LB-100` (merge-path-truth) and `PLAN-LB-120` before opening new work.

## Sources

- `plan-v2-86-core-store-tests-b-006` (chained merge after `blocked`)
- `plan-v2-86-core-store-tests-b-007` (stale holder blocked admission for 240 s)
- Both archived verbatim at `lessons-routing/inbox/archive/plan-v2-86-core-store-tests-b/`.
