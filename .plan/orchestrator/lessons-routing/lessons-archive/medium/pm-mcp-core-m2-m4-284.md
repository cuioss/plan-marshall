envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:51Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-030.md
> RECURRENCE of -208, -222, -260, -269. New: two execute boundary rows record a measured zero for envelopes that did work. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Record dispatch boundaries for finalize steps and never write all-zero usage rows

- Source: plan-retrospective (plan-09-audit-trail), aspects logging-gap-analysis, execution-context-dispatch-audit, log-analysis.
- Suggested component: `plan-marshall:phase-6-finalize` (dispatcher, record-dispatch-boundary call) / `plan-marshall:plan-marshall` (execution workflow, usage forwarding).

## Context

Finalize spent 5.1M of the plan's 10.6M tokens across 36 dispatch resolves, yet no `work/metrics-dispatch-boundaries-6-finalize.toon` exists. The dispatch audit therefore reports `firing_comparison` for 6-finalize as `not_evaluated`, and 9 of 11 terminal finalize steps have no token evidence (`no_evidence`), with channel confidence `low` (4 finalize dispatch lines against 33 completions). Separately, 2 of the 9 execute boundary rows (14:19:14Z and 16:07:28Z) record 0 tokens, 0 tool uses and 0 ms for envelopes that completed fix tasks.

## Root cause

The finalize dispatcher did not call `record-dispatch-boundary` after its step dispatches, and on two execute returns the recorder was called without the agent's usage figures, which the recorder stores as a measured zero.

## Proposed action

Make the finalize dispatcher record one boundary row per dispatched step (with `--step-id`), and have the orchestrator refuse or mark `unmeasured` instead of writing `0` when it has no usage figures for a return.

## Evidence

- logging-gap-analysis: "6-finalize recorded no dispatch-boundary rows"; "2 execute dispatch-boundary rows carry all-zero usage"
- execution-context-dispatch-audit: dispatch_coverage 2 dispatched / 9 no_evidence of 11; channel_completeness ratio 0.121, confidence low; firing_comparison 6-finalize not_evaluated
- log-analysis: dispatch_boundaries 5-execute rows with total_tokens 0 at 14:19:14Z and 16:07:28Z
