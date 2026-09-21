envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:12Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Worked and Wall totals print the same (n=5/6) marker over different phase sets

## Context

This plan's `metrics.md` Phase Breakdown Total row reads:

```
| **Total** | **4h46m (n=5/6)** | **3h13m (n=5/6)** | **1h10m (n=5/6)** | ...
             Worked              Reported (wall)      Idle
```

The Worked total exceeds the Wall total by 1h33m. The two figures are not
comparable, because the `(n=5/6)` marker on each covers a different five phases:

- Worked `n=5/6` omits **1-init**, which recorded no worked figure.
- Wall `n=5/6` omits **6-finalize**, which carries no `end_time` — and 6-finalize is
  the single largest phase of the run (2h43m worked, 5.58M tokens, 70 pct of plan
  tokens).

`totals_worked_ms_population_count: 5` and `totals_wall_ms_population_count: 5` are
both truthfully 5. The marker publishes the population *size* and says nothing about
the population *membership*, so two disjoint-in-one-member sets render identically.

## Root cause

The coverage marker was designed as a completeness signal (`k of N`) and is being
read as a comparability signal. Two columns bearing the same `(n=k/N)` invite a
reader to compare them, and here that comparison is invalid in the specific way the
marker was meant to prevent.

Worked exceeding Wall is the visible symptom. It is documented as possible
(`plan-efficiency.md` explicitly warns against assuming Worked <= Wall), which means
the one signal a reader might use to notice the mismatch is pre-explained away.

## Proposed action

1. Render the marker with membership when two columns' populations differ, not only
   the count — e.g. `(n=5/6, less 1-init)` and `(n=5/6, less 6-finalize)`.
2. Or emit an explicit incomparability note on the Total row whenever any two
   columns' population *sets* differ, independent of their sizes.
3. `generate` already computes each `{field}_population_count`; the membership is
   available at the same point, so this is a render-site change, not a new
   measurement.

## Evidence

- metrics.md Phase Breakdown — 1-init Worked is `-`, 6-finalize Wall is `-`
- work/metrics.toon — `totals_worked_ms: 17162077`, `totals_wall_ms: 11598000`, both with `population_count: 5`
- aspect: plan_efficiency — the ratio computation had to name both membership sets to state its own numerator honestly
- `phases_missing_end_time: [6-finalize]` — the report already knows which phase the wall total is missing
