envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T19:18:14Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall

# Finalize cost 2.24x execute — on a full-posture plan the apparatus now costs twice the work it checks

Measured spend for this plan (5.26M tokens total, phase-1 tokens unrecorded):

| Phase | Tokens | Share |
|---|---:|---:|
| 2-refine | 185,188 | 4% |
| 3-outline | 468,174 | 9% |
| 4-plan | 793,827 | 15% |
| 5-execute | 1,176,599 | 22% |
| **6-finalize** | **2,639,930** | **50%** |

Inside finalize, the largest line items:

- `pre-submission-self-review` — **860,069** (33% of finalize, 16% of the plan) over **4**
  dispatch passes
- `finalize-step-security-audit` — **320,150**
- `project:finalize-step-lessons-housekeeping` — **228,797**
- `finalize-step-simplify` — **159,048** for a **0-edit, 0-finding** result
- plus two full loop-backs, each re-running `verify:quality-gate` + `verify:module-tests`

**This is not an argument that the spend was waste.** It bought: 9 real self-review defects
(including the structurally-unreachable guard), a CWE-1333 ReDoS in operator-ingested
content, 12 actionable CodeRabbit findings, and the corroborated `fan_out_marker` defect
that TASK-013 fixed structurally. On the evidence, the review apparatus out-produced the
implementation phase in defects-found-per-token. The plan is honestly better for it.

What is worth the epic's attention is the **shape**, and that nothing surfaces it:

1. **No artifact shows the operator this ratio.** `metrics.md` is generated at phase-6 entry
   and prints finalize as `unrecorded`, so the one document designed to answer "where did
   this plan's cost go?" omits half of it. (Filed separately as the three-disagreeing-totals
   defect.)
2. **`finalize-step-simplify` cost 159K to find nothing** on a plan whose own outline was
   graded `simplicity=lean`. A step whose expected yield is near-zero for a given plan shape
   is a lane-lever candidate, not a fixed cost.
3. **`pre-submission-self-review` needed 4 passes.** Passes 3 and 4 each found real defects
   (`c1ee26` unreachable guard, `59d44c` docstring misattribution), so stopping at 2 would
   have shipped them. The 4-pass cost is *earned* here — but it means the step's cost is
   unbounded by design and nothing budgets it.

## Solution

- **Publish the finalize:execute ratio as a first-class metric** in the phase breakdown, and
  regenerate `metrics.md` at plan close so it is visible without a retrospective.
- **Treat near-zero-yield finalize steps as lane levers, not fixed cost.** `simplify` on a
  `simplicity=lean` plan is the clearest instance; the existing lane machinery can already
  express it.
- **Give `pre-submission-self-review` a declared pass budget with an explicit
  budget-exhausted outcome**, so a 4-pass run is a visible decision rather than an emergent
  one. Do not cap it silently — the 4th pass paid for itself here.

## Impact

Applies to every `full`-posture plan. The actionable half is instrumentation and lane-lever
placement, not cutting review depth — this run is evidence that the depth is what caught the
defects.
