envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:23:51Z

component=plan-marshall:manage-metrics
category=improvement
bundle=plan-marshall
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=plan-efficiency,log-analysis

# Fold an unclosed phase's dispatch-boundary rows into generate rather than publishing a 2.5M-token undercount

`metrics.md` for PR #1126 publishes:

```text
| **Total** | **3h14m (n=4/6)** | ... | **2,392,836 (n=4/6)** | ... |
> Partial: unrecorded phases — 6-finalize
```

Meanwhile `work/metrics-dispatch-boundaries-6-finalize.toon` holds **12 rows totalling 2,507,354 tokens** — *more than the entire published total*. The plan's real dispatched spend is **4,900,190**, so the headline understates it by 51%.

The data needed to close the gap is already on disk, written by `record-dispatch-boundary` during the same phase.

## Root cause

`generate`'s completeness verdict keys a phase's *recorded* status solely off `end_time`. A phase that dispatched twelve times and recorded every one of them is still "unrecorded" if its terminal close never fired — and the terminal close is the last thing a finalize does, so `6-finalize` is the phase most likely to be missing it and the phase most likely to hold the largest figure.

## Solution

When a phase has no `end_time` but DOES have a `metrics-dispatch-boundaries-{phase}.toon`, fold that file's row sum into the phase's `Tokens` cell as a **labelled** figure (the same default-plus-exception labelling discipline the `(inline)` / `(mixed)` markers already use — e.g. `(from dispatch boundaries)`), and mark the Total accordingly. Keep the `partial` verdict for duration, which the boundaries file cannot supply honestly.

## Impact

The `(n=4/6)` marker is *honest* — this is not a truthfulness bug, it is a usefulness one. But every downstream consumer that reads the total is reading a floor: the plan-efficiency anchors score against `totals.tokens`, and on this plan the published figure would have scored the run at roughly half its real cost against every ratio threshold. A partiality marker that is technically correct and practically ignored is how a 2.5M-token phase disappears from a cost review.

Precedent in the same skill: `enrich` already folds inline main-context tokens into a zero-dispatch phase's `total_tokens` and labels the row `total_tokens_population: inline` so no consumer misreads it. This is the same move for the same reason, applied to the dispatched population.
