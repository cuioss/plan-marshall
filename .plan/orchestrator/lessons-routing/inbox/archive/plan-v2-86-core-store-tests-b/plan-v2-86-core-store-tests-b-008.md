envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:33Z

# Build wrapper auto-files findings for a failing module the plan did not touch, and they block the merge gate until handled by hand

- component: plan-marshall:build-maven
- category: improvement
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

verify -Pcoverage failed only in pm-runtime (LspClientTest.stubborn timeout under host load), a module the PR does not touch. The build wrapper still filed 6 build-error/test-failure findings against the plan, and the merge gate stayed blocked until they were resolved by hand as accepted. Such findings could be marked as outside the plan's footprint, or kept apart from merge-blocking findings.

Evidence: findings 92a0ea, 51c151, d0228b, e61c38, 8dfd68, 60bf46 of plan-v2-86-core-store-tests-b (resolution accepted, with the passing re-run recorded).
