envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:22:25Z

component=plan-marshall:manage-metrics
category=improvement
confidence=medium
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# Billing and composition columns render a measured-looking 0 over an empty population

## Context

This plan's persisted aggregate carries:

```
totals_billing_weighted_total: 0
totals_billing_weighted_total_population_count: 0
```

and every one of the six phase blocks carries `inline_main_context_tokens: unmeasured`. In `metrics.md` the `Billing (cost)` column renders `-` on all six rows and `-` in the Total — correct and legible. In `work/metrics.toon` and in the `generate` TOON return, the same fact is a bare `0`.

The composition split is absent on the same terms: all 17 dispatch-boundary rows across three phases list `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens` in `unmeasured_columns`, so `context_position_cost` reports `measured_rows: 0` and `position_multiple: unmeasured`.

The metrics store already does the hard part — it publishes the population count beside the total, so the absence *is* recoverable. The gap is that the total and its population count are two independent reads, and a consumer that takes only the total gets a number that is indistinguishable from a measured zero cost.

## Root cause

`0` is being used as the neutral element of a sum over an empty set. That is arithmetically right and semantically wrong for a reported figure: "no phase reported a billing weight" and "every phase reported a billing weight of zero" are different states, and only the population count separates them. The rendered report already refuses to conflate them (`-`, not `0`); the persisted record does not.

## Proposed action

Make the persisted aggregate carry the absence in the value, not only beside it — e.g. omit `totals_billing_weighted_total` entirely when its population count is 0, matching the discipline `generate` already applies to denominators (a denominator that could not be read is **omitted**, never written as `0`, precisely so a persisted `0` can be trusted as measured). The same rule applied to `totals_*` would make the two families consistent.

This matters beyond cosmetics because billing composition is the measurement the token-reduction work depends on. A plan whose composition is structurally unmeasured should be excluded from any cross-plan composition roll-up, and today it would average in as a zero.

## Evidence

- `work/metrics.toon` — `totals_billing_weighted_total: 0`, `totals_billing_weighted_total_population_count: 0`; `inline_main_context_tokens: unmeasured` on all six phase blocks
- aspect: log_analysis — `context_position_cost`: `total_rows: 17`, `measured_rows: 0`, `unmeasured_rows: 17`, `position_multiple: unmeasured`
- aspect: plan_efficiency — `billing_composition.status: not_measured` over `total_phases: 6`
- `manage-metrics/standards/data-format.md` § "Denominators and Their Sampling Point" — the omit-rather-than-zero rule this proposal extends to the `totals_*` family
