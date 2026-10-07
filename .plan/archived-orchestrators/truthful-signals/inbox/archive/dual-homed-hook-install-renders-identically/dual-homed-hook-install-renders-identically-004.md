envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:48:43Z
lifecycle=superseded
superseded_by=dual-homed-hook-install-renders-identically-010.md

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=dual-homed-hook-install-renders-identically
source_aspects=logging_gap_analysis,plan_efficiency,execution_context_dispatch_audit

# The largest finalize dispatch recorded no dispatch-boundary row

## Context

`manage-metrics reconcile-ledgers` over this plan returns 22 findings and `union_rows: 30` against `execution_log_rows: 24` and `boundary_rows: 14` — only 8 rows paired. The two ledgers disagree in both directions on the same phase, and the biggest disagreement is the single largest dispatch of the run:

- `pre-submission-self-review`'s 5th firing — **953,588 tokens, 1,773,582 ms** — has a `record-step` row and **no** `record-dispatch-boundary` row.
- Three errored finalize dispatches worth **491,732 tokens** have boundary rows and **no** `record-step` row.

The consequence is that `check-dispatch-audit`'s `channel_completeness` reports `dispatch_line_count: 10` against `completion_count: 25` (`ratio: 0.4`, `confidence: low`), and the DISPATCH_TERMINATION_CAUSE distribution renders as a complete-looking per-cause breakdown over 14 rows while the run's most expensive dispatch carries no cause at all. Every consumer that sums one ledger under-reports; `metrics.md`'s `6-finalize` row (2,002,514) is at least **673,584 tokens** below the union floor of 2,676,098.

## Root cause

`record-step` and `record-dispatch-boundary` are written by independent call sites with no shared transaction and no shared key — a boundary row carries no `step_id`, so the two can only be joined on phase plus a time window. Nothing enforces that a dispatch which recorded one recorded the other. The finalize dispatcher's re-firing path in particular appears to record the step outcome without the paired boundary write.

## Proposed action

1. Make the pairing structural rather than conventional: have the finalize dispatcher's post-return handler write both records from one place, or have `record-dispatch-boundary` accept and persist the `step_id` so the join stops depending on a 300-second window.
2. Until then, surface the divergence where it is read: `check-dispatch-audit`'s `channel_completeness` should publish the `reconcile-ledgers` union count beside its own row count, so a `confidence: low` names the specific rows it is missing rather than only a ratio.

## Evidence

- `manage-metrics reconcile-ledgers --plan-id dual-homed-hook-install-renders-identically`: `findings_count: 22`, `union_rows: 30`, `execution_log_rows: 24`, `boundary_rows: 14`
- finding `row_absent_from_boundary_ledger`, `step_id: pre-submission-self-review`, `total_tokens: 953588`, `2026-09-03T05:53:33Z`
- findings `row_absent_from_execution_log` at 18:06:28Z (221,480), 18:13:33Z (187,333), 23:39:46Z (82,919)
- aspect: execution_context_dispatch_audit — `channel_completeness.ratio: 0.4`, `confidence: low`
- aspect: plan_efficiency — `ledger_reconciliation.tokens_absent_from_the_metrics_row: 673584`
