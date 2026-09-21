envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:02:09Z

component=plan-marshall:manage-metrics
category=improvement
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Wire the per-dispatch context-load fields, or the billing view stays unmeasurable

## Context

`record-dispatch-boundary` accepts four context-load flags — `--input-tokens`,
`--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens` —
each documented as "Omit when unmeasured; the column is written as `unmeasured`,
NOT as 0".

No dispatch site passes them. Across this plan:

```
context_position_cost:
  total_rows: 28   measured_rows: 0   unmeasured_rows: 28
  by_phase: 4-plan 1/0, 5-execute 10/0, 6-finalize 17/0
  position_multiple: unmeasured
```

And in `metrics.md`, the `Billing (cost)` column is empty for all six phases and for
the Total (`totals_billing_weighted_total_population_count: 0`). `manage-metrics
enrich` — the only producer of the four-field view and the `billing_weighted_total`
— appears in none of the 23 steps of this plan's finalize chain.

The consequence: a plan that consumed **6,568,833 tokens** over **22h29m** has no
billing-composition measurement of any kind.

## Root cause

The recorder and the renderer were both built and both behave correctly. The
emission side was never wired, and `enrich` remained an optional verb that no
lifecycle step invokes.

Worth stating plainly: the gap is *detectable only because* the reader is honest. If
those 28 rows had defaulted the four columns to `0`, this would read as a measured
zero-cache run and would average into every cross-plan roll-up as such. The
truthfulness work already landed is what makes the missing producer visible — and
visibility is where it stopped.

## Proposed action

- Forward the four `message.usage` fields at every `record-dispatch-boundary` call
  site.
- Add `manage-metrics enrich` to the finalize step chain (it needs the session id,
  which `platform_runtime session capture` already persists), so the four-field
  per-phase view and `billing_weighted_total` are populated as a matter of course
  rather than on request.

## Why this matters beyond one plan

The repository's stated first priority is token reduction, and the dominant billing
term is context re-read (`cache_read`), which is exactly what these four fields
measure and what nothing currently records. Every lever aimed at that term is
presently unmeasurable on live plans.

## Evidence

- aspect log_analysis: `context_position_cost` — 0 of 28 rows measured
- `manage-metrics generate` → `totals_billing_weighted_total_population_count: 0`
- `metrics.md` Billing (cost) column: `-` on every row including Total
- `execution.toon` `phase_6.steps` — 23 steps, no `enrich`
