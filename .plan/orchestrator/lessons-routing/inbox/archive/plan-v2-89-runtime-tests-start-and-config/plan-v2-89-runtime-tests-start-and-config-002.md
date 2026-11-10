envelope_version=1
sender_type=plan
sender_id=plan-v2-89-runtime-tests-start-and-config
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T17:36:58Z

# record-dispatch-boundary was called without --step-id on all 20 rows, so firing_comparison paired none of them with the execution log

- component: plan-marshall:plan-marshall
- category: improvement
- source plan: plan-v2-89-runtime-tests-start-and-config (pm-mcp-core, PR 302)

Every record-dispatch-boundary call of the orchestrator omitted --step-id, so the dispatch audit's firing_comparison paired 0 of 20 rows with the execution log. The workflow text does not make --step-id look mandatory for a dispatch that is not a plan step, and nothing rejects the omission.

Evidence: the execution-context dispatch audit aspect of the retrospective report.
