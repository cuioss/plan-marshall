envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:18:39Z

component=plan-marshall:manage-metrics
category=improvement
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# A run can cost 3.5M tokens and leave no record of what it cost to buy

## Context

There are two independent paths to a cost measurement for a plan, and this run left
both empty.

**Path 1 — per-dispatch.** `record-dispatch-boundary` accepts four context-load columns
(`--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`,
`--cache-creation-input-tokens`). Their contract is explicit that an omitted flag writes
the literal `unmeasured` so that "the caller passed no measurement" stays distinguishable
from "the dispatch loaded zero context". This run recorded 11 dispatch-boundary rows
across `4-plan` (1), `5-execute` (2) and `6-finalize` (8). Every one of them carries
`unmeasured` in all four columns:

```
context_position_cost:
  total_rows: 11
  measured_rows: 0
  unmeasured_rows: 11
  position_multiple: unmeasured
  position_multiple_basis: unmeasured
```

The mechanism worked exactly as designed — it reported honestly that nothing was
measured. What is absent is any call site that supplies the values.

**Path 2 — per-phase.** `manage-metrics enrich` walks the session transcripts and writes
the four-field `message.usage` view plus the derived `billing_weighted_total` per phase.
It never ran for this plan. `generate` reports
`totals_billing_weighted_total: 0` with `totals_billing_weighted_total_population_count: 0`,
and `metrics.md` renders `-` in the `Billing (cost)` column for all six phases.

So the run has a dispatched-token total of 3,547,890 (itself a floor — `6-finalize` was
still open) and **no cost figure at all**. Given that `cache_read` is typically the
large majority of billing weight, the dispatched figure is not a proxy for cost; it
answers a different question, and the report says so.

This matters beyond bookkeeping. The plan contributes zero rows to the per-dispatch
context-load corpus — the substrate for any position-cost or context-growth analysis.
A corpus assembled from runs like this one has a population of zero and will report it
as such, which is the honest outcome, but the measurement is simply not being taken.

## Root cause

The four columns are optional at the writer and unsupplied at every caller. Nothing
downstream treats an all-`unmeasured` ledger as a defect: `analyze-logs` reports
`measured_rows: 0` faithfully, and no gate reads it. Similarly, `enrich` is not part of
the finalize step set for this plan's manifest, so the per-phase view is never
populated, and `generate`'s zero-population billing total is reported without comment.

Both halves fail open in the same way — they report the absence correctly and nobody
consumes the report.

## Proposed action

1. **Populate the per-dispatch columns at the dispatcher.** The dispatcher already
   parses the returned `<usage>` envelope for `total_tokens` / `tool_uses` /
   `duration_ms`; the four-field view is available in the same place. Forward it.
2. **Make an all-unmeasured ledger visible.** Have `analyze-logs` (or the retrospective's
   logging-gap aspect) emit a finding when `measured_rows == 0` and `total_rows > 0` —
   the population is known, so this is a derivable zero, not an assumed one.
3. **Decide whether `enrich` belongs in the finalize step set.** If the billing column
   is intended to be populated for every plan, `enrich` must run before `record-metrics`
   closes `6-finalize`. If it is genuinely opt-in, `metrics.md` should say the column is
   unpopulated by configuration rather than rendering a bare `-` that reads as zero.

## Evidence

- aspect: log_analysis — `context_position_cost: total_rows 11, measured_rows 0,
  unmeasured_rows 11, position_multiple: unmeasured`.
- aspect: log_analysis — every `dispatch_boundaries` row lists all four columns under
  `unmeasured_columns`.
- artifact: `metrics.md` — `Billing (cost)` column renders `-` for all six phases;
  Total row renders `-`.
- script return: `manage-metrics generate` — `totals_billing_weighted_total: 0`,
  `totals_billing_weighted_total_population_count: 0`.
- contract: `manage-metrics/SKILL.md` § `record-dispatch-boundary`, the four-way
  measured / unmeasured / unrecognised / indeterminate reader contract.
