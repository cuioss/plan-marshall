envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:30:01Z

# The context-load channel recorded zero measured rows across all 33 dispatches

component: plan-marshall:manage-metrics
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

`analyze-logs` `context_position_cost` for this plan:

```
total_rows:       33
measured_rows:     0
unmeasured_rows:  33
position_multiple: unmeasured
by_phase: 4-plan unmeasured, 5-execute unmeasured, 6-finalize unmeasured
```

Every one of the 33 dispatch-boundary rows carries
`unmeasured_columns: [input_tokens, output_tokens, cache_read_input_tokens,
cache_creation_input_tokens]`. Not one dispatch passed the four context-load
flags to `record-dispatch-boundary`.

The same absence shows up in three more places on the same plan:

- `metrics.toon`: `inline_main_context_tokens: unmeasured` on all six phase rows
- `generate`: `totals_billing_weighted_total: 0` with
  `totals_billing_weighted_total_population_count: 0`
- `metrics.md`: the whole `Billing (cost)` column renders `-`

Root cause of the last three: `enrich` never ran for this plan.

## Why this belongs to this epic specifically

`code-intelligence-substrate` rests on the measurement that context — cache reads
across turns — carries the overwhelming majority of billing weight, while
dispatched-work tokens carry little. On a 10.1M-token plan the channel that
measures exactly that produced **zero measured rows**. The epic's primary
instrument was dark for the whole run.

Note the honest part: every surface reported `unmeasured` rather than `0`. The
plumbing for truthful absence works. What is missing is the measurement itself.

## The generalizable rule

An instrument that is correct and never fed is indistinguishable, in the corpus,
from one that was never built. Two separable fixes: (1) make the finalize path
run `enrich` before `generate` so the four-field view and `billing_weighted_total`
exist at all; (2) have the dispatcher forward the four `message.usage` fields to
`record-dispatch-boundary` at every termination, since the row already reserves
the columns. Until then, no cross-plan context-cost figure can be computed from
this corpus, and any that is quoted is built on `population_count: 0`.
