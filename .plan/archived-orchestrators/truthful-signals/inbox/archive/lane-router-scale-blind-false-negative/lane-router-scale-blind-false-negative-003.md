envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:49:31Z

component=plan-marshall:ref-workflow-architecture
category=anti-pattern
bundle=plan-marshall

# A detector that re-derives a subset of its producer's rules WILL drift — consume the producer's verdict

This plan reproduced its own target defect **three separate times**, and each recurrence
had the identical mechanic: the gate re-derived a *subset* of the sensor's
classification rules instead of asking the sensor.

- Recurrence 1: `scan_incomplete` — the gate re-implemented part of the completeness
  rule and diverged from the sensor's.
- Recurrence 2: `fan_out_marker` — same shape, different predicate.
- Recurrence 3: same shape again, after the first two had been fixed.

Each fix was local and each fix was correct, and the defect still came back, because the
fixes addressed the *instances* while leaving intact the structure that generates them:
two independent expressions of one decision, kept in agreement only by vigilance.

Note the compounding: the plan whose whole subject was "the router issues a confident
verdict without consulting its evidence" itself repeatedly built gates that issued
verdicts without consulting the sensor. The archetype is self-reproducing under review.

## Solution

Fixed structurally in TASK-013: the detector now **calls `classify_scope_pure` and
consumes the band it returns**. Gate and sensor are one decision by construction, so
there is no longer a second expression that can drift.

The general rule:

> When a consumer needs to know what a producer decided, **call the producer and use its
> verdict**. Do not re-derive "just the part I need" — a subset re-derivation is a second
> source of truth wearing a smaller coat, and it will drift.

Diagnostic for review: if you can point at two places that must *agree* about the same
classification, you have already found the defect, whether or not they currently agree.
Ask "what would make agreement structural?" rather than "are these two in sync?".

## Impact

Applies to every gate/sensor, detector/classifier, and validator/producer pair. This is
the structural remedy for the recurring "the plan reproduces the defect it is fixing"
archetype in this class: local fixes to a re-derivation do not stop the recurrence,
collapsing the two derivations into one does.
