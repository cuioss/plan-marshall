envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:31Z

# merge_lock acquire 'blocked' can be followed by a pre_merge_gate merge chained in the same call

- component: plan-marshall:manage-locks
- category: anti-pattern
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

In branch-cleanup, merge_lock acquire returned admission=blocked and the ci pr merge-queue enqueue still ran in the same shell call, without the plan holding the cross-plan merge mutex. The cause was an orchestrator procedure error (commands chained without checking the admission result). The merge gate should refuse to enqueue unless it can prove that the calling plan holds the lock, so this cannot be done by chaining commands.

Evidence: work log WARNING of plan-v2-86-core-store-tests-b: 'merge_lock acquire returned admission=blocked (holder plan-v2-89-runtime-tests-start-and-config, liveness not_live) after 240s, and the pre_merge_gate merge was dispatched in the same shell call WITHOUT this plan holding the cross-plan merge mutex'.
