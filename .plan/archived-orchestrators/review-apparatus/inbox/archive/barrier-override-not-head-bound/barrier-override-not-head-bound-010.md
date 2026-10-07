envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:25Z

# check-routing-decisions blames the prune predicate for a posture-cutoff drop

component: plan-marshall:plan-retrospective
category: bug
confidence: high

## Context

The routing-decisions aspect emitted:

```
mis_prune_checks[2]{check,status,predicate,removal_cause,detail}:
  "mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

That reads as a prune-predicate defect: the `no_code_delta` predicate wrongly fired on a footprint that
did touch production code. It is not what happened. `decision.log` records the actual removal:

```
[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps (execution_profile=standard):
effective tier full exceeds the standard posture cutoff
```

The step was dropped by the posture cutoff, deliberately, before any predicate ran.

## Root cause

`removal_cause` defaults to `predicate_evaluated` for any absent prunable step, without consulting the
`lane_resolution` decision-log entries that record the real cause. The script already parses those
entries — they appear verbatim in its own `recorded_lane_decisions[4]` output block — so the information
is in hand and simply not used for attribution.

## Proposed action

Set `removal_cause` from the matching `lane_resolution` entry when one exists (`posture_cutoff`,
`explicit_off_override`, `core_floor_immune`), and only fall back to `predicate_evaluated` when no
lane_resolution entry names the step. A step dropped by posture is an intended configuration outcome, not
a mis-prune, and must not be graded as `fail`.

## Evidence

- aspect: routing_decisions — `mis_prune:sonar-roundtrip,fail,no_code_delta,predicate_evaluated`
- aspect: routing_decisions — the same fragment's `recorded_lane_decisions[4]` carries the contradicting posture-cutoff entry
- decision.log 06:35:30 `[9e1b0f]` — the authoritative removal record
