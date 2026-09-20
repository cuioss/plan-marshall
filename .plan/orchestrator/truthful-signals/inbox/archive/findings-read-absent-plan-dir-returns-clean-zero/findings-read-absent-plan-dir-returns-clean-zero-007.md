envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:43Z

component=plan-marshall:manage-metrics
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# Two disjoint phase populations rendered under an identical (n=k/6) marker print Worked above Wall

## Observed

The generated `metrics.md` Total row for this plan reads:

| | Worked | Reported (wall) | Idle | Tokens | Tool Uses | Billing |
|---|---|---|---|---|---|---|
| **Total** | **8h55m (n=5/6)** | **7h6m (n=5/6)** | **3h32m (n=5/6)** | **6,608,198 (n=5/6)** | **2005 (n=5/6)** | **-** |

**Worked (8h55m) exceeds Wall (7h6m).** For one population that is impossible: worked time is
bounded above by wall time, and the codebase enforces exactly that invariant per row
(`agent_duration_ms` is clamped to the accumulated wall span).

The rows explain it. `Worked` sums phases **2, 3, 4, 5, 6** — `1-init` has no worked figure.
`Wall` sums phases **1, 2, 3, 4, 5** — `6-finalize` has no `end_time`, so no wall span. Two
five-member populations that **share only four members**, presented under an identical marker.

## Why the existing marker cannot catch it

`(n=5/6)` discloses the **size** of the population, not its **membership**. Both columns are
honestly size-5-of-6. The marker is therefore incapable of distinguishing "same five phases" from
"two different fives", and the reader is invited to compare two columns that do not cover the same
work. The invariant the per-row clamp guarantees is silently violated at the Total row, by
aggregation rather than by arithmetic.

This is the epic's archetype in a compact form: a correctly-computed, correctly-labelled figure
whose label answers a different question from the one the reader is asking.

## Secondary observation from the same table

The `Billing (cost)` column is empty for every phase and for the Total
(`totals_billing_weighted_total: 0` over `totals_billing_weighted_total_population_count: 0`),
because `manage-metrics enrich` was never run for this plan. The field-level pairing is honest —
a zero beside a zero population count — but the rendered cell is a bare dash, so the report cannot
answer what the plan cost to buy. Given that cache-read re-reads carry the overwhelming majority of
billing weight, the absent column is the one most worth having.

## Remedy (for the epic to scope)

1. **Render membership, not just size.** Either name the phases each column covers, or emit a
   distinct marker when two columns in the same Total row cover different sets.
2. **Suppress or flag the cross-column comparison** when the populations differ. A Total row whose
   Worked exceeds its Wall should say so explicitly rather than leave the reader to notice.
3. Consider whether `generate` should run `enrich` (or refuse to render the Billing column as a
   bare dash) so the cost measure is not silently absent for a whole plan.
