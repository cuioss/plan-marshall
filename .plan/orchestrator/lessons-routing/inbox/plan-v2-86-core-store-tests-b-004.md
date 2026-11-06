envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:30Z

# Every commit after the reviews closed invalidates functional-review, code-review, security-audit and the pre-push gate (verdict_inputs undeclared => unconditional re-fire)

- component: plan-marshall:phase-6-finalize
- category: improvement
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

Because the review steps declare no verdict_inputs, any new head commit invalidates all head-dependent verdicts, so a small PR-review fix costs a full re-review cycle. In PLAN-V2-86 a 10-file inline-fix commit triggered a new security audit (~104k tokens), functional review (~450k tokens, delta round plus closing full round), code review (~670k tokens), the pre-push gate, push and ci-verify. If each step declared which input paths its verdict depends on, a delta commit would re-fire only the reviews it actually affects.

Evidence: verdict_currency classify for functional-review, code-review, security-audit and pre-push-quality-gate each returned verdict: invalidated, reason: verdict_inputs_undeclared at head 5e812fe5; token figures from the accumulate-agent-usage records of plan-v2-86-core-store-tests-b.
