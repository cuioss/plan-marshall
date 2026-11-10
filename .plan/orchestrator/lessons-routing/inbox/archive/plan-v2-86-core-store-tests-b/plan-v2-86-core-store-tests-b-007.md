envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:32Z

# A stale merge-lock holder (liveness not_live, location not_found) blocked admission for 240 s

- component: plan-marshall:manage-locks
- category: bug
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

The holder plan-v2-89-runtime-tests-start-and-config had liveness not_live and location not_found in merge_lock queue-list, yet it still blocked the FIFO admission of this plan for the whole 240 s wait. If the holder is not live and its location cannot be found, the lock should be reclaimed (or the waiter promoted), not waited out.

Evidence: merge_lock queue-list: entries position 0 plan-v2-89-runtime-tests-start-and-config liveness not_live location not_found, lock_held true; acquire --wait-seconds 240 returned status blocked.
