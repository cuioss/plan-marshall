envelope_version=1
sender_type=plan
sender_id=lb-49-opencode-measurement
epic=live-blockers
kind=candidate-lesson
created=2026-10-22T11:23:26Z

# Dispatch-boundary rows record no step id and no spend

## Context

Seventeen dispatch-boundary rows were recorded for this plan (1 in `4-plan`,
3 in `5-execute`, 13 in `6-finalize`). Every one is keyless: `firing_comparison`
reports `keyless_boundary_rows` 1/3/13 and `paired_firings: 0` across all three
phases, against 63 `execution_log` rows that therefore pair with nothing.
Every row also carries `total_tokens: 0`, `tool_uses: 0`, `duration_ms: 0` and
all four context-load columns `unmeasured`, so the per-dispatch ledger records
*that* a dispatch ended and why, but never what it cost.

The retrospective's `channel_completeness` consequently lands at
`confidence: low` (11 finalize-scoped dispatch lines against 43 completions),
and `dispatch_coverage` classifies 10 of 16 finalize steps as `no_evidence`.

## Root cause

`record-dispatch-boundary` is being called at the right moment with the
termination cause but without `--step-id` and without the agent-reported
figures the dispatcher already returns. On a target that could not yet measure
tokens (this plan's own subject) the figures genuinely were zero — but the step
id was available and is simply not forwarded.

## Proposed action

Forward `--step-id` on every `record-dispatch-boundary` call from the finalize
dispatcher and the execute loop, and forward the returned
`total_tokens`/`tool_uses`/`duration_ms` and the four context-load figures when
the harness supplies them. Where they are genuinely absent, leave them
unmeasured rather than zero, so the ledger distinguishes "no spend" from "not
measured". Then `reconcile-ledgers` can pair on the key instead of falling back
to timestamp windows.

## Evidence

- aspect: execution_context_dispatch_audit — firing_comparison: 17 keyless boundary rows, 0 paired firings, 63 unpaired execution rows; channel_completeness ratio 0.256, confidence low
- aspect: log_analysis — dispatch_boundaries: all 17 rows total_tokens 0, tool_uses 0, duration_ms 0, four columns unmeasured
- aspect: logging_gap_analysis — DISPATCH_TERMINATION_CAUSE per-phase distributions, all with zero recorded spend
