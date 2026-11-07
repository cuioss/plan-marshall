envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T20:34:32Z

component=plan-marshall:plan-marshall
category=improvement
confidence=high
source_plan=plan-v2-93-http-tests-annotations

# Record dispatch token totals and step keys from the measurement, not by hand

## Context

In plan-v2-93 the orchestrator forwarded every dispatch's token figures to `accumulate-agent-usage` / `record-dispatch-boundary` by typing them. Once it logged an estimated 150000 tokens instead of the measured 90215. None of the 11 boundary rows carries `--step-id` or the four context-load columns, and the 21 `execution_log` rows carry no token measurement. The dispatch audit therefore paired 0 firings, finalize dispatch coverage is `no_evidence` for 12 of 12 steps (channel confidence low), and `context_position_cost` is unmeasured on every row.

## Root cause

The recording calls take free-typed numbers and an optional key, so the orchestrator can estimate a figure and skip the key without any check failing.

## Proposed action

Have the recording seam read the just-returned dispatch's measured usage from the runtime (the `<usage>` record) instead of a typed figure, and make `--step-id` required on `record-dispatch-boundary` for dispatches that have a step (finalize steps, execute envelopes). Reject a figure that does not match the measured usage, or record it as `unrecognised`.

## Evidence

- plan-efficiency: token-accounting slip, estimate 150000 vs measured 90215
- execution-context-dispatch-audit: firing_comparison 0 paired, 11 keyless boundary rows, 21 unmeasured execution rows, channel confidence low
- log-analysis: context_position_cost measured_rows 0 of 11
- llm-to-script-opportunities: per-dispatch hand-forwarding, about 23 repetitions per plan
