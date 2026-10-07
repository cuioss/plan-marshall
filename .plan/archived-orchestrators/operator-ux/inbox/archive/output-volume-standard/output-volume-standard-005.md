envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T11:10:00Z

# Finalize cost 3.7x execute on a three-file documentation-only change

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium
source_plan: output-volume-standard
source_aspects: plan_efficiency, manifest_decisions

## Context

This plan changed three markdown files. No source, no tests, no config. Its recorded spend:

| Phase | Tokens | Worked |
|---|---:|---:|
| 2-refine | 149,600 | 7m28s |
| 3-outline | 459,744 | 17m0s |
| 4-plan | 355,687 | 8m24s |
| 5-execute | 306,719 | 28m37s |
| **6-finalize** | **1,122,327** | **28m58s** |
| Total (floor, n=5/6) | 2,394,077 | 1h30m |

6-finalize alone is 47% of a floor total, and 3.7x what 5-execute spent producing the entire
diff. Three of the four fallback ratio thresholds for `surgical + enhancement` tripped:
`tokens_per_file_modified` 798K (threshold 50K), `total_tokens_per_deliverable` 798K
(threshold 500K), `worked_seconds_per_task` 1810s (threshold 900s, itself uncalibrated for a
worked-time numerator).

## Root cause

The docs-only footprint was known and the manifest did narrow the step set — `scope_gated_finalize`
dropped `project:finalize-step-plugin-doctor` and `pre-submission-self-review` on
`scope_estimate=surgical`, and `lane_resolution` dropped `finalize-step-security-audit`,
`sonar-roundtrip` and `adr-propose` on `execution_profile=standard`. Five candidates removed,
and finalize still ran 21 steps and dispatched 6 of them.

So the gating that exists keys on **scope estimate** and **execution profile** — never on the
realized footprint's *kind*. A three-file documentation diff and a three-file production diff
resolve to the same `surgical` bucket and get the same 21 steps. The six dispatched steps each
cost 124K-291K tokens; the expensive ones (`automatic-review` at 291K, review-retrospective at
188K) are review machinery weighing a diff that contains no executable code.

Note the manifest's own recorded reason for keeping one gate: `pre_push_quality_gate_inactive —
kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable`. At compose
time the footprint was not yet knowable, which is exactly why a compose-time scope estimate
cannot substitute for it.

## Proposed action

Do not propose dropping steps on a static rule — propose making the footprint's *kind* a gating
input the way `scope_estimate` already is:

- The manifest already re-derives a diff at `branch-cleanup` time (`docs_only_diff` is a
  declared rule, skipped here only because `verification_steps` was non-empty). Consider a
  mid-finalize re-gate that consults the realized footprint once it exists, rather than only at
  compose time when it is admittedly unresolvable.
- Investigate whether the review-weighted steps (`automatic-review`, review-retrospective) can
  take a cheaper lane on a footprint with no executable delta. `manifest_decisions` already
  records `branch_cleanup_changes: pass — branch-cleanup paired with 3 changed file(s)` and
  classifies all three as `documentation`, so the classification exists; nothing consumes it.

Recording this as an observation, not a settled fix: the right cut is a design question for the
epic, and the numbers above are the input to it.

## Evidence

- aspect: `plan_efficiency` — 3 of 4 fallback thresholds tripped; `dominant_phase
  6-finalize=1122327`; every total is a floor because 6-finalize carries no `end_time`.
- aspect: `manifest_decisions` — `filtered_by_category.documentation: 3`, every other category 0;
  5 candidate steps dropped by scope and lane gating, 21 retained.
- aspect: `log_analysis` — the 6 finalize dispatch-boundary rows, all `step_complete`, totalling
  1,122,327 tokens with zero error and zero retryable spend. The cost is not waste from failed
  dispatches; it is the price of the retained step set.
