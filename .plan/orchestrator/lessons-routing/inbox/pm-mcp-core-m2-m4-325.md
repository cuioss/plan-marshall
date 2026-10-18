envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:33Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source=plan-retrospective (execution-context-dispatch-audit, logging-gap-analysis, plan-efficiency)

# Record dispatch boundaries and tokens for finalize dispatches

## Context

Finalize of plan-74-credential-store-choice ran about 30 dispatches (functional and code review 7 firings each, their verifiers, three triage passes, bot and Sonar passes). No `work/metrics-dispatch-boundaries-6-finalize.toon` was written, the 6-finalize row of metrics.md renders tokens `unknown`, and the dispatch audit classifies 10 of 11 terminal finalize steps as `no_evidence` (0 dispatched) with channel confidence `low` (7 finalize dispatch lines against 32 completions).

## Root cause

The finalize dispatcher does not call `manage-metrics record-dispatch-boundary` (nor attribute `<usage>` tokens) for its step dispatches, so the largest review spend of the plan is invisible to every metrics and audit consumer.

## Proposed action

Record one dispatch-boundary row per finalize step dispatch (including review authors, verifiers and triage) with its termination cause (`returned_with_findings` for productive loop-backs), and fold the tokens into the 6-finalize accumulator so the plan total is no longer a floor.

## Evidence

- aspect: execution-context-dispatch-audit — dispatch_coverage 0 dispatched / 1 inline / 10 no_evidence of 11; firing_comparison 6-finalize not_evaluated (no boundary file)
- aspect: plan-efficiency — totals_tokens 5,625,778 n=4/6, 6-finalize unknown
- aspect: logging-gap-analysis — DISPATCH_TERMINATION_CAUSE covers only 4-plan and 5-execute
