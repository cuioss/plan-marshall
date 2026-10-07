envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:27:44Z

component=plan-marshall:manage-metrics
category=bug
title=A finalize loop-back destroys the prior pass's phase token attribution, and the phase-window overlap it creates is computed but never rendered

# A loop-back silently overwrote 73% of 5-execute's token attribution, and metrics.md still shows the pre-corruption number

## Observation

Plan `exploration-share-is-unmeasured` took two finalize loop-back iterations. Comparing the two on-disk artifacts:

| Source | 5-execute end_time | 5-execute total_tokens |
|---|---|---|
| `metrics.md` (generated 2026-07-28T20:37:01Z) | 2026-07-28T20:37:01Z | **1,032,929** |
| `work/metrics.toon` (updated 2026-07-29T06:37:44Z) | 2026-07-29T06:37:44Z | **278,562** |

`end-phase` is documented as replace-not-accumulate: *"Calling `end-phase` multiple times for the same phase replaces the previous end data (does not accumulate)."* The loop-back re-entered 5-execute and re-closed it, and the second close **replaced** the first pass's totals — a 73% loss. Nothing warned.

Two further consequences fall out of the same write:

1. **The phase windows now overlap.** `5-execute.end_time` (2026-07-29T06:37:44Z) is roughly **10 hours later** than `6-finalize.start_time` (2026-07-28T20:37:01Z). Every window-scoped attribution `enrich` performs is computed against overlapping windows.
2. **The violation is computed and never shown.** `generate` emits a `boundary_monotonicity[]` list for exactly this condition. `metrics.md` was never regenerated after the loop-back, so the violation sits on disk, detected by nobody, while the stale rendered report keeps displaying the pre-corruption figure.

The stale render also carries a now-inverted justification. For 5-execute it prints:

> Dispatch-boundary total: 1,032,929 (recorded; not preferred — smaller than total_tokens under same-population max)

After the rewrite the dispatch-boundary total is **3.7x larger** than `total_tokens` (278,562), so the printed reason is factually backwards. Prose rendered once and never revalidated became a false explanation.

## Rule

- **Re-closing a phase must not silently discard the prior close.** Either accumulate across re-closes, or persist per-pass rows and have `generate` sum them. A destructive overwrite of measurement data needs, at minimum, a recorded prior value.
- **A computed invariant violation that is only rendered on demand is not detected.** `boundary_monotonicity[]` existed and fired; nobody called `generate` again. Either regenerate at the point of the mutating write, or have consumers read `work/metrics.toon` directly rather than the possibly-stale `metrics.md`.
- **Rendered prose that explains a comparison must be regenerated with the comparison.** A justification string ("not preferred — smaller than…") is a derived claim, not a label, and goes stale exactly like a number.

## Why it matters here specifically

This plan's entire deliverable set is token measurement (ten per-phase exploration counters, a corpus-wide audit check, a token-economics denominator). Its own token attribution was corrupted by a routine loop-back, and three separate token oracles now disagree by 3.3x with none labelled authoritative:

- `metrics.md` Total: **2,479,022** (n=4/6 phases)
- `check-routing-decisions` `cost_preview.actual_tokens`: **1,147,273**
- accumulator + live `metrics.toon` floor: **3,810,333**

## Residue

Nothing is fixed. Owed: (a) loop-back-safe accumulation, (b) a regenerate-or-read-source rule so `boundary_monotonicity` violations surface, (c) an authoritative-oracle designation so the three totals stop competing.
