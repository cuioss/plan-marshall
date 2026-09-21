envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:12:39Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# check-routing-decisions labels a phase-6-only token sum as the plan's actual_tokens

`check-routing-decisions` emitted:

```toon
cost_preview:
  actual_tokens: 974134
  predicted_tokens: null
```

`974134` is **not** the plan's actual token cost. It is the exact sum of the
`record-step` entries for phase 6 alone:

```
78968 + 47466 + 196865 + 255921 + 140442 + 70067 + 43815 + 140590 = 974134
```

The plan's own `metrics.md` independently records `1,409,073` tokens for phases
2 through 5, with 1-init unrecorded. The true total is at least **2,383,207** —
2.4× the number the field labelled `actual_tokens` reports.

## Why this is a truthfulness defect, not a rounding one

The field name makes a whole-plan claim. Any consumer comparing
`cost_preview.actual_tokens` against a lane-selection budget, a scope anchor, or
a predicted cost is comparing a budget against 41% of the spend. In this plan the
difference is decision-relevant: `974,134` sits *under* the `single_module +
bug_fix` warning anchor of 800K only by being over it modestly, while the true
`2,383,207` crosses the **error** anchor of 1.3M outright. The mislabelled field
turns an error-severity budget overrun into an unremarkable number.

## Corrective action

Either rename the field to what it measures (`phase_6_recorded_step_tokens`) or
compute the real total. The clean fix is a `manage-metrics total --plan-id`
verb that sums every recorded population — per-phase metrics plus per-step
records — and returns the total together with an explicit
`unmeasured_phases[]` list, so a partial total is never presented as a complete
one. `metrics.md` already models this correctly with its `(n=4/6)` annotations;
`cost_preview` does not.

## Evidence

- aspect: routing_decisions — `cost_preview.actual_tokens: 974134`
- aspect: plan_efficiency — `totals.tokens: 2383207` (lower bound; 1-init
  unmeasured)
- decision.log `record-step` lines for 6-finalize sum to exactly 974134
- metrics.md — `**Total** 1,409,073 (n=4/6)` for phases 2-5
