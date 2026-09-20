envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:24:56Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=plan_efficiency,logging_gap_analysis

# plan-efficiency always reads a metrics.md that predates 6-finalize

## Context

The `plan-efficiency` aspect names `metrics.md` as its primary input. For this plan, metrics.md
was generated at `2026-08-09 16:23:40 UTC` — the 5-execute close — and carries:

```
| 6-finalize | - | - | - | - | - | - |
| **Total**  | **2h19m (n=4/6)** | ... | **1,717,844 (n=4/6)** | **673 (n=4/6)** | - |
> Partial: unrecorded phases — 6-finalize
```

6-finalize was in fact the single most expensive phase of the plan: seven dispatched steps
totalling 902,037 tokens over 3h49m of wall time, more than 5-execute's 440,614. Every one of
those figures was already on disk in `work/metrics-dispatch-boundaries-6-finalize.toon` while
the aspect ran.

## Root cause

This is a manifest step-ordering property, not a one-off. In `execution.toon` `phase_6.steps`,
`plan-marshall:plan-retrospective` is step 17 of 22 and `record-metrics` is step 20. The
retrospective therefore always runs three steps before the metrics for its own phase are
folded in, so the efficiency aspect is structurally blind to 6-finalize on every plan, not just
this one.

The partiality machinery behaved correctly throughout — `partial: true`, `n=4/6` column
markers, and the `> Partial: unrecorded phases` banner all fired. The floor was labelled as a
floor. The gap is that the aspect consuming it has no way to raise the floor even though the
data exists.

## Proposed action

Either:

1. have the plan-efficiency aspect read `work/metrics-dispatch-boundaries-{phase}.toon`
   directly in addition to metrics.md, reconstructing the in-flight phase's dispatched total
   and labelling its provenance; or
2. run a `manage-metrics generate` immediately before the retrospective step so metrics.md is
   current up to that point.

Option 1 is preferable: it does not depend on step ordering staying put, and it keeps the
reconstruction's provenance explicit rather than making a stale report look fresh.

## Evidence

- aspect: plan_efficiency — `tokens_provenance.metrics_md_figure: 1717844`, `metrics_md_partial: true`, `reconstructed_addend: 902037` from the seven recorded dispatch-boundary rows
- artifact: `metrics.md` generated 16:23:40; the retrospective dispatch began 20:06:19
- manifest: `execution.toon` `phase_6.steps` — plan-retrospective at index 17, record-metrics at index 20

## Consequence in this run

The reconstruction mattered for the verdict, though not for its direction. metrics.md's own
partial 1.72M already crosses the `multi_module+bug_fix` warning anchor at 1.2M; the
reconstructed 2.62M crosses the *error* anchor at 2.0M. So the aspect would have emitted a
finding either way, but at the wrong severity, and would have named 5-execute as the dominant
phase when it was in fact 6-finalize.
