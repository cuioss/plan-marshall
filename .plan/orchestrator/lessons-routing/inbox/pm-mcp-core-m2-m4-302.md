envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:09Z

# Candidate lesson: pass --step-id and context-load figures to record-dispatch-boundary

Component: plan-marshall:plan-marshall and plan-marshall:phase-6-finalize (dispatch bookkeeping; version 0.1.1947)
Category: improvement
Source: plan-retrospective of work-package-redistribution (execution-context dispatch audit, log analysis)

## Context

All 7 dispatch-boundary rows of this plan (4-plan 2, 5-execute 3, 6-finalize 2) were recorded without `--step-id`
and without the four context-load figures (input, output, cache read, cache creation). As a result:

- the dispatch audit's firing comparison paired 0 rows in every phase (all boundary rows keyless);
- context-position cost is unmeasured for 7 of 7 rows, and the Billing column of metrics.md is empty;
- 9 of 11 finalize steps carry no token record at all, so the audit cannot say whether they ran inline or were
  dispatched (channel confidence: low);
- the 1-init phase recorded no token figure, so every total is a floor (n=5/6).

## Root cause

The orchestrator's calls to `record-dispatch-boundary` omit the optional flags the reconciliation depends on, and
inline finalize steps record no zero-token attribution.

## Proposed action

- Forward the dispatch's step key as `--step-id` on every `record-dispatch-boundary` call, and the context-load
  figures when the runtime reports them.
- Have inline finalize steps record an explicit zero-token attribution so "ran inline" is measured, not inferred.

## Evidence

- execution-context-dispatch-audit: firing_comparison keyless_boundary_rows 2/3/2, paired_firings 0;
  dispatch_coverage dispatched 2, no_evidence 9 of 11
- log-analysis: context_position_cost measured_rows 0 of 7
- metrics.md: Tokens unknown for 1-init; totals_billing_weighted_total population 0
