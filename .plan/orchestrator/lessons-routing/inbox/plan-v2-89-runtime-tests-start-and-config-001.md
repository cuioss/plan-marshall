envelope_version=1
sender_type=plan
sender_id=plan-v2-89-runtime-tests-start-and-config
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T17:36:57Z

# Returns that handed a build back are recorded as voluntary_checkpoint instead of verification_handback

- component: plan-marshall:plan-marshall
- category: bug
- source plan: plan-v2-89-runtime-tests-start-and-config (pm-mcp-core, PR 302)

In 5-execute, three leaf returns that handed a build back to the orchestrator were recorded with record-dispatch-boundary as voluntary_checkpoint. record-dispatch-boundary rejected verification_handback for these returns, so the only accepted value that fits was the wrong one, and the retrospective then counted them as voluntary stops.

Evidence: the dispatch-boundary rows of the plan's metrics; the retrospective report section on dispatch boundaries (quality-verification-report.md in the plan's archive).
