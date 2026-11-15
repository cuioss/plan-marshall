envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T13:17:30Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall

# Record a dispatch-boundary row and returned usage for every finalize and cancelled dispatch

- component: plan-marshall:plan-marshall
- category: bug
- confidence: high

## Context

plan-v2-140 ran about 13 phase-5 dispatches and about 8 phase-6 subagent dispatches: functional-review and code-review twice each, their verifiers, and automatic-review. The 5-execute boundary ledger holds 11 rows. The 6-finalize ledger holds one `step_complete` row with 0 tokens. The envelope-4 dispatch that the weekly API limit killed (HTTP 429) has no `harness_cancellation` row. Its resumed return, which completed TASK-10, has no row either. All 14 `execution_log` rows record `total_tokens=unmeasured`. So `metrics.md` reports 1-init and 6-finalize tokens as unknown, the total is a floor (n=4/6), and the dispatch audit grades its channel confidence `low` (12 of 12 finalize steps `no_evidence`).

## Root cause

The orchestrator calls `record-dispatch-boundary` and `record-step` without the usage the subagent return carries. On a harness-terminated dispatch it records nothing at all. The finalize dispatcher does not stamp a boundary row per dispatched step.

## Proposed action

After every subagent return, including a failed or cancelled task notification, call `record-dispatch-boundary` with the termination cause (`harness_cancellation` for a 429 or a timeout) and the returned `total_tokens` / `tool_uses` / `duration_ms`. Forward the same figures to `record-step`. Run `manage-metrics enrich` before `record-metrics`, so the inline phases get a main-context figure.

## Evidence

- logging-gap-analysis: 11 boundary rows for 13 execute dispatches; 1 row for the finalize dispatches
- execution-context-dispatch-audit: dispatch_coverage 0 dispatched / 0 inline / 12 no_evidence; channel_completeness confidence=low (ratio 0.286)
- routing-decisions cost_preview: execution_log_rows_measured 0 of 14
- metrics.md: Tokens unknown for 1-init and 6-finalize; Total 3,473,686 (n=4/6)
- chat history: task-notification "Agent terminated early due to an API error: You've hit your weekly limit"
