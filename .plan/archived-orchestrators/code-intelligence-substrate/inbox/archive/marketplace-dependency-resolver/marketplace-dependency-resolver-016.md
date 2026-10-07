envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:18:57Z

component=plan-marshall:plan-retrospective
category=bug
title=Read the recorded lane_resolution cause instead of re-deriving a prune predicate

# Read the recorded lane_resolution cause instead of re-deriving a prune predicate

## Context

`check-routing-decisions` emitted, for this plan:

```
mis_prune_checks[2]{check,status,predicate,removal_cause,detail}:
  "mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,
    sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

`sonar-roundtrip` was never skipped as `no_code_delta`. Four lines below, in the
**same fragment**, sits the recorded reason:

```
recorded_lane_decisions[4]:
  … lane_resolution — dropped sonar-roundtrip from phase_6.steps
    (execution_profile=standard): effective tier full exceeds the standard posture cutoff
```

The step was dropped by the posture cutoff, which is a correct and intentional
decision for `execution_profile=standard`. The checker reports a mis-prune
against a predicate that never ran.

## Root cause

The checker **re-evaluates** a prune predicate against the realized footprint and
attributes the removal to whichever predicate it happens to evaluate, rather than
**reading** the removal cause the composer already recorded. Its `removal_cause`
field says `predicate_evaluated` — which is an honest description of what the
checker did, and precisely the problem: what the checker did is not what the
composer did.

The authoritative cause is already in the fragment's own
`recorded_lane_decisions[]` array. The checker prints it and does not consult it.

This produces a confident false positive of exactly the shape this epic tracks: a
`fail` status, a specific named predicate, and a plausible-sounding message, all
refuted by adjacent data in the same output.

## Proposed action

1. When a `lane_resolution` decision entry exists naming the removed step, that
   entry is authoritative for `removal_cause`. The prune-predicate
   re-evaluation must only run for steps with **no** recorded removal decision.
2. Add a distinct outcome for "removed by posture/profile, not by a prune
   predicate" so it never renders as `mis_prune … fail`.
3. Add a self-consistency assertion: a `mis_prune` finding whose named predicate
   contradicts a `recorded_lane_decisions[]` entry for the same step is a
   checker defect and must fail the checker's own tests.

## Evidence

- aspect: routing_decisions — the `fail` row and the contradicting
  `recorded_lane_decisions[]` entry, both in `fragment-routing-decisions.toon`.
- aspect: manifest_decisions — the same composer entry appears in
  `decision_log_entries[]`, timestamped 2026-08-01T13:25:10Z, hash `9e1b0f`.
- The plan's `execution_profile` is `standard`; `sonar-roundtrip` is a `full`-tier
  step, so its removal is the documented, correct behaviour.
