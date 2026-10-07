envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:25:20Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=routing_decisions,manifest_decisions

# check-routing-decisions attributes a posture-cutoff removal to a prune predicate

## Context

`check-routing-decisions` emitted a `fail`:

```
mis_prune_checks[2]{check,status,predicate,removal_cause,detail}:
  "mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,
    sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

The realized footprint did touch production code — seven source files — so the *observation* is
correct. The *attribution* is not. In the same fragment, four lines further down, the script
prints the decision-log entry that records why sonar-roundtrip was actually removed:

```
[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps
  (execution_profile=standard): effective tier full exceeds the standard posture cutoff
```

sonar-roundtrip was dropped by the **standard posture cutoff**, alongside
finalize-step-security-audit which was dropped for the identical stated reason. The
`no_code_delta` predicate was never the operative cause of its absence.

## Root cause

`removal_cause: predicate_evaluated` is asserted for an absent prunable step without
reconciling against the `lane_resolution` decision-log entries the script has already parsed
and is about to print as `recorded_lane_decisions[4]`. An element can leave `phase_6.steps` by
at least three routes — predicate prune, posture cutoff, explicit `off` override — and all
three appear in this plan's own log (`adr-propose` was dropped by an explicit `off` override).
The check collapses them to one.

## Proposed action

Reconcile `removal_cause` against the `lane_resolution` entries before evaluating the mis-prune
predicate. When an entry attributes the removal to a posture cutoff or an explicit override,
set `removal_cause` accordingly and skip the predicate check — a step removed by configured
posture cannot be a mis-prune, because the predicate never ran. Reserve
`predicate_evaluated` for steps whose removal the log attributes to the predicate, and add
`removal_cause: unattributed` for the case where no entry explains the absence.

## LLM counterfactual (this run)

The correct posture verdict for `sonar-roundtrip` in this plan is **correctly pruned by
configured posture**, not OVER-pruned. `execution_profile=standard` was set at 1-init and the
cutoff behaved as configured. The `fail` should not have been emitted.

The sibling check `mis_prune:finalize-step-simplify` passed correctly (`removal_cause:
not_removed`, "step ran"), so the failure is specific to the removed-step branch.

## Evidence

- aspect: routing_decisions — `summary: passed 1, failed 1`, `llm_judgement_required: true`
- same fragment, `recorded_lane_decisions[4]` — the posture-cutoff entry for sonar-roundtrip and the identical entry for finalize-step-security-audit
- aspect: manifest_decisions — `decision_log_entries` carries the same four `lane_resolution` lines
