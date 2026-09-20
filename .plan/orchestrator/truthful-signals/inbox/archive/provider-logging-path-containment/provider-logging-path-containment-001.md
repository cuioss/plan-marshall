envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:31Z

# Candidate lesson L1 — One phase carries three disagreeing token totals and the smallest is published as settled

- component: `plan-marshall:manage-metrics`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

Phase `5-execute` of this plan carries **three mutually inconsistent token totals** in three on-disk stores:

| Store | Value |
|---|---|
| `metrics.md` Phase Breakdown row | 374,662 |
| `work/metrics.toon` `[5-execute].total_tokens` | 541,712 |
| `work/metrics-dispatch-boundaries-5-execute.toon` (sum of 4 rows) | 874,945 |

Spread: **2.34x**. The phase has an `end_time`, so `generate`'s partiality verdict treats it as **fully recorded** — `partial` is driven by the presence of `end_time` alone. The smallest of the three figures is therefore rendered in the report as a settled, non-partial fact.

The same pattern holds at plan level. `metrics.md` publishes a Total of **1,424,544** and honestly flags it `n=4/6`, but `6-finalize` alone dispatched **~2,753,885** tokens across 15 boundary rows. The published headline under-reports measured dispatch spend by roughly **66%**.

A fourth mechanism disagrees again: `check-routing-decisions` reports `cost_preview.actual_tokens: 1,995,966`, which is exactly the `execution.toon` `execution_log` sum for 6-finalize — a different population from either of the above, presented without a population label.

## Why the existing mitigation does not cover this

The `partial` / `unrecorded_phases` mechanism (#812, floor-not-truth) works correctly for a phase that never closed. It has no concept of a phase that closed, was **re-entered via loop-back**, and whose rendered row was never regenerated. This plan looped back `6-finalize -> 5-execute` twice (19:32Z and 21:08Z); `metrics.toon` advanced `[5-execute].end_time` to 20:16:52Z, but `metrics.md` was last generated at 16:21:03Z and still shows the pre-loop-back end time and token count.

## Proposed remedy

1. A `reconcile` verb on `manage-metrics` that reads all three stores, emits per-phase agreement/disagreement, and **refuses to publish a single blended total** across populations that are not declared subsets of one another.
2. Treat a phase whose `close_count > 1` (the field already exists — `[5-execute].close_count: 2`) as **stale in the rendered report** unless `metrics.md` was generated after the latest `end_time`. `partial: false` must not certify a row generated before its own store was last written.
