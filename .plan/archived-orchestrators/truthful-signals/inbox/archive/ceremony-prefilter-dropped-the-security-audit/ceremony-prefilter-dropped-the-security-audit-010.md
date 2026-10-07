envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:54:00Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-29

# Three token-accounting artifacts each stop recording at a different time and none says so

This plan produced three independent records of its own cost. Each is internally clean. All three
are floors, and not one of them says it is a floor:

| Artifact | Value | Last data point | Phase actually ran to |
|---|---|---|---|
| `metrics.md` | 1,626,375 tokens, "unrecorded phases — 6-finalize" | 11:05:54Z | 16:40:00Z |
| `work/metrics-accumulator-6-finalize.toon` | 2,759,215 tokens, 13 samples | 14:38:11Z | 16:40:00Z |
| `work/metrics-dispatch-boundaries-6-finalize.toon` | 7 rows | 12:58:22Z | 16:40:00Z (19 steps done) |

`metrics.md` is the one a human reads, and it is the worst of the three: it renders a tidy
five-of-six-phase table totalling **1.63M**, while the true plan floor — folding in the accumulator
it did not read — is **4.39M**. That is a **2.7× understatement**, presented with a `Partial:` marker
that names the *phase* but gives no hint of the magnitude.

The accumulator is subtler and arguably worse, because it carries no partiality marker at all. It
stopped at 14:38:11Z; roughly two further hours of finalize (three automatic-review barrier rounds,
the merge-path incident, lessons-capture, preference-emitter, branch-cleanup) contributed tokens
that no artifact anywhere records. Nothing distinguishes "this accumulator finished" from "this
accumulator stopped being called".

## Solution

- **Give the accumulator a terminal marker.** `end-phase` / `phase-boundary` should stamp a
  `closed: true` field; an accumulator without it is *open*, and any total derived from it must be
  rendered as a floor.
- **Have `generate` fold the accumulator into the reported total even when the phase is still
  open**, labelled as a floor, instead of omitting the phase and reporting a total that is wrong by
  a multiple.
- **Make the `Partial:` marker quantitative.** `Partial: unrecorded phases — 6-finalize` should read
  `Partial: 6-finalize open, ≥2,759,215 tokens accumulated and not included in the Total`.
- **Cross-check the three artifacts.** A `record-metrics` step that finds their last-data-point
  timestamps spread across four hours should say so rather than emit a clean report.

## Impact

Affects every plan's cost record, and therefore every budget anchor in
`plan-retrospective/references/plan-efficiency.md` — the calibration table's thresholds are being
compared against systematically understated totals. It also silently rewards long finalize phases:
the longer finalize runs past the last accumulator write, the cleaner and cheaper the plan looks.
