envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:24:39Z

component=plan-marshall:phase-6-finalize
category=bug
title=Record dispatch boundaries and token totals for 6-finalize steps

# Record dispatch boundaries and token totals for 6-finalize steps

## Context

Every one of the 12 `6-finalize` rows in the execution manifest's `execution_log` carries `total_tokens: unmeasured`, `tool_uses: unmeasured` and `duration_ms: unmeasured`. No `work/metrics-dispatch-boundaries-6-finalize.toon` is written at all, although the equivalent files exist for `4-plan` and `5-execute`. As a result `check-dispatch-audit` classifies 16 of 16 terminal finalize steps as `no_evidence` (0 `dispatched`, 0 `ran_inline`) and downgrades its own `channel_completeness` confidence to `low` on a ratio of 0.25. The `firing_comparison` block reports `6-finalize` as `not_evaluated` with the explicit reason that the boundary side of the comparison is unknown.

## Root cause

The finalize dispatcher does not call `manage-metrics record-dispatch-boundary` for its step dispatches, and no token attribution is captured for them, so both independent evidence sources the dispatch audit relies on are empty for this phase.

## Proposed action

Emit a `record-dispatch-boundary` row per finalize step dispatch, and capture the step's token record, so `6-finalize` produces the same boundary artifact `4-plan` and `5-execute` already produce. The logging-gap reference already names this file as the one place a review-shaped dispatch's `returned_with_findings` and `error` rows can land; until it is written, the phase carrying the majority of finalize dispatch spend is audited by nothing.

## Evidence

- aspect: execution_context_dispatch_audit — `dispatch_coverage: 0 dispatched / 0 ran_inline / 16 no_evidence of 16`; `channel_completeness.confidence: low`, `ratio: 0.25`
- aspect: execution_context_dispatch_audit — `firing_comparison.6-finalize.state: not_evaluated`, 12 execution rows against 0 boundary rows
- aspect: logging_gap_analysis — gap `6-finalize / DISPATCH_TERMINATION_CAUSE`
- aspect: plan_efficiency — the `6-finalize` row renders `-` in every column
