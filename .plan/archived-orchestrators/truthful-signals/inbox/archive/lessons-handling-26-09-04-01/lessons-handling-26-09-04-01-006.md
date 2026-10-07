envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:51:47Z

component=plan-marshall:manage-findings
category=improvement

# A deliberate negative control files real-looking failure records that later block the merge gate

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`).

## Observation

TASK-10 of that plan ran a proof-of-discrimination: it deleted a `families.remove`
call so a new test would fail, demonstrating that the test actually discriminates
rather than passing vacuously. This is correct testing practice — a negative control
is the only evidence a gate is not lying.

The control filed **12 build-error / test-failure findings** into the plan's findings
store. Those findings SURVIVED the control's revert. At the pre-merge barrier they
were indistinguishable from genuine failures and BLOCKED the barrier. The only way to
tell them apart afterwards was timestamp correlation against the task log — a
reconstruction, not a record.

## The generalisable rule

A deliberate negative control is EXPECTED to pollute the findings store. That is not a
side effect to tolerate quietly; it is a predictable consequence with a predictable
downstream cost at the merge gate.

Provenance has to be stamped **when the record is created**, not recovered at triage
time. Once the control is reverted, the only distinguishing signal left is a
timestamp, and a timestamp is correlation rather than attribution.

## Suggested remedy

Give the findings surface a way to mark records as produced under an intentional
negative control — a flag on the emitting call, or a scoped "control window" opened
and closed around the deliberate breakage — so that:

1. Triage can partition control-produced findings from genuine ones by reading a
   field, not by reconstructing a timeline.
2. The pre-merge barrier can exclude them without an operator override that also
   waives genuine failures.

Absent such a mechanism, the workflow rule is: a task that runs a negative control
must record, in the same step, which findings the control produced.

## Cross-reference

The originating plan was itself about gate truthfulness. The irony is load-bearing: a
mechanism that exists to prove one gate is honest generated records that made a
different gate dishonest about what was actually wrong.
