envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:30:07Z

# Dispatch-boundary rows carry no step_id, so per-step token attribution never pairs, and interim usage is recorded instead of final usage

- component: plan-marshall:manage-metrics (record-dispatch-boundary) / plan-retrospective check-dispatch-audit
- category: improvement
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

All 26 dispatch-boundary rows of this plan are keyless and leave their input/output/cache columns unmeasured. The retrospective's firing_comparison therefore paired 0 of 25 finalize and 0 of 3 execute execution rows, and context_position_cost is unmeasured on every row. Separately, one boundary row (5-execute, envelope 1, second run) recorded 410470 tokens and 160 tool uses while the agent's final usage was 421934 and 186, because that leaf returned an interim notification while its own background work continued. Boundary rows should carry a step_id, and the orchestrator contract should say to record the final usage, not the interim one.

Evidence: retrospective fragment-execution-context-dispatch-audit firing_comparison (keyless_boundary_rows 1/9/16, paired_firings 0); fragment-log-analysis context_position_cost; decision log entry ed5796 of 2026-11-05T18:53:48Z.
