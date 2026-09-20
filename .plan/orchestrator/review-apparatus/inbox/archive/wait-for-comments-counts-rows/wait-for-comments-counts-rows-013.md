envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:45:47Z

# Finalize outspent the entire fix it was shipping (1.72M vs 1.60M tokens)

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

Budget accounting for a `single_module` + `bug_fix` plan that modified 12 files across 3 tasks and
2 deliverables:

| Phase | Tokens | Wall |
|---|---:|---:|
| 1-init | — | 3m28s |
| 2-refine | 138,961 | 6m20s |
| 3-outline | 659,140 | 30m11s |
| 4-plan | 361,951 | 2h04m |
| 5-execute | 439,389 | 2h11m |
| **6-finalize** | **1,723,509** | **~2h01m** |
| **Total** | **3,322,950** | **~6h58m** |

The `single_module + bug_fix` calibration anchor is **warning at 800K / error at 1.3M tokens** and
**warning at 60 min / error at 90 min**. Observed: **2.6x the token error anchor** and **4.6x the
wall-clock error anchor**. Every fallback ratio also trips: `tokens_per_file_modified=276,913`
(warning at 50K), `seconds_per_task=8,352` (warning at 900), `max_phase_token_share=0.52`
(warning at 0.50), `total_tokens_per_deliverable=1,661,475` (warning at 500K).

Finalize alone (1.72M) outspent phases 2-5 combined (1.60M). Identified drivers:

- **~605K on one step.** `pre-push-quality-gate` was dispatched twice — the first dispatch terminated
  with `termination_cause=error` after 222,900 tokens and 34 tool uses; the retry completed with
  382,431. No `work.log` ERROR line names what failed in the first attempt.
- **Two discarded build cycles** in phase 5 (see the build-timeout candidate-lesson).
- **4-plan spent 1h50m idle against 14m36s worked** — 88% of that phase's wall-clock was orchestrator
  wait, not work.
- **Deep planning lane on a concretely-specified single_module bug fix.** `planning_lane=deep` with
  `scope_estimate=single_module` and 7 concretely-named affected files; 3-outline consumed 659K, the
  second-largest phase.

## Root cause

Not a single defect — a compounding of an un-retried-step cost (605K), an under-set build ceiling
(two discarded cycles), and a lane/posture selection that bought deep discovery for a change the
request had already localized to a named predicate in a named file.

## Proposed action

- Record the failure reason on a `termination_cause=error` dispatch boundary, so a 222K-token loss is
  attributable rather than anonymous.
- Re-examine whether the deep lane is warranted when the request body names concrete file paths AND
  `scope_estimate` is `surgical`/`single_module` — the S5 concreteness signal exists precisely for
  this case; check why it did not bias light here.
- Treat "finalize token spend exceeds the sum of phases 2-5" as a first-class retrospective alarm; it
  is a stable, cheap indicator that the shipping apparatus, not the change, is the cost centre.

## Evidence

- aspect: plan_efficiency — 6 `[BUDGET]` findings, 2 at `error` severity against the `single_module+bug_fix` anchor row.
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 10 rows; `2026-08-01T15:59:03Z` `termination_cause=error total_tokens=222900`, `2026-08-01T16:18:59Z` `step_complete total_tokens=382431`.
- `metrics.md` — 4-plan `Reported (wall-clock) 2h4m`, `Worked 14m36s`, `Idle 1h50m`.
- `status.metadata.planning_lane=deep`, `references.scope_estimate=single_module`, `change_type=bug_fix`.
