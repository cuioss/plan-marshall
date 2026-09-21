envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:57:28Z

# check-routing-decisions attributes a posture prune to the predicate it re-evaluated

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

`check-routing-decisions` re-evaluates each absent prunable step's `prunable_when` predicate against
the realized footprint. For this plan it emitted:

```
mis_prune_checks[2]{check,status,predicate,removal_cause,detail}:
  "mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
  "mis_prune:finalize-step-simplify",pass,no_code_delta,not_removed,step ran
```

`sonar-roundtrip` was not skipped as `no_code_delta`. The recorded lane-resolution decision — which
the **same fragment** prints verbatim two blocks lower under `recorded_lane_decisions` — says:

> `[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps (execution_profile=standard):
> effective tier full exceeds the standard posture cutoff`

The step was removed by the **posture cutoff**, not by the predicate. So a correct, intentional
posture prune is reported as a mis-prune failure, with `removal_cause: predicate_evaluated`
asserting a cause the log in hand contradicts.

The consequence is a false FAIL in the retrospective's routing verdict (`summary: passed 1, failed 1`)
that a reader must go read the decision log to refute — which is exactly the work the aspect exists
to save.

## Root cause

The check re-runs the predicate against the footprint whenever a prunable step is **absent**, and
labels the result `removal_cause: predicate_evaluated` unconditionally. Absence is treated as
implying predicate-driven removal. But `lane_resolution` has at least three removal causes visible in
this plan's own decision log — posture cutoff (`sonar-roundtrip`, `finalize-step-security-audit`),
explicit `off` override (`adr-propose`), and predicate — and only the third makes the predicate
re-evaluation meaningful.

## Proposed action

1. Read the removal cause from the `lane_resolution` decision-log entry the script already parses
   (it emits them in `recorded_lane_decisions`), and set `removal_cause` from it:
   `posture_cutoff` / `explicit_off_override` / `predicate_evaluated` / `unrecorded`.
2. Run the mis-prune predicate check **only** when `removal_cause == predicate_evaluated`. For a
   posture or override removal, report `status: skip` with the real cause, not `fail`.
3. When no `lane_resolution` entry names the step, report `removal_cause: unrecorded` and skip rather
   than assuming the predicate — a step absent for an unrecorded reason is a could-not-tell, not a
   mis-prune.

## Evidence

- `work/fragment-routing-decisions.toon` — the `mis_prune_checks` row and the
  `recorded_lane_decisions` block, in the same fragment, disagreeing.
- `logs/decision.log` `12:39:08Z` — the three distinct removal causes recorded by
  `manage-execution-manifest:compose` for this plan.
- aspect `routing_decisions` (`llm_judgement_required: true`, `summary.failed: 1`).

## Why this belongs to truthful-signals

The script has the true cause in hand — it prints it — and still asserts a different one. That makes
the fragment self-refuting to a careful reader and confidently wrong to a fast one, and the wrongness
lands in a `fail` verdict rather than in prose. It is also, uncomfortably, a defect in the
retrospective apparatus itself: the tool that audits routing honesty is the one misattributing.
