envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:24Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# The non-vacuity control written to prove one finding fixed was itself unable to fail

## What happened

CodeRabbit filed `d10934` against
`marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py:332`
— an exception-contract defect. The fix for it added a **matched negative control**: a test whose
job is to prove the guard can distinguish the failing case from the passing one, so the positive
test cannot pass vacuously.

CodeRabbit then filed `e40f03` against that very control, at
`test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness_required_coverage_unresolvable_plan_root.py:115`.
The control **could not fail**: it asserted a condition that a second production route yields
identically, so it would have passed whether or not the guard worked.

The remediation for a defect introduced a fresh instance of the archetype the remediation existed
to close, in the same run, in the file written to prove the closure.

## Why the internal pass could not catch it

Both findings are classified `gate_structural` in this plan's review-versus-gate delta — no lint,
type-check or test-gate class reaches either, however configured. `e40f03` specifically
"requires knowing what the control was written to exclude, and that a second production route
yields the same value." That is a two-fact join across production and test code, and the
`ext-self-review-plan-marshall` candidate surfacers do not currently produce it.

This is at least the seventh recorded instance of the vacuous-guard archetype, and — as in
several prior instances — it was **introduced by a fix for a vacuous guard**. The archetype is not
merely recurring; it reproduces through its own remediation.

## The generalisable rule

A negative control is only a control if it can be shown to fail. Writing one is not enough;
**demonstrating that it fails when the guard is removed** is the whole of its value. A control
asserted but never falsified is indistinguishable from a comment.

## Candidate surfacer for ext-self-review-plan-marshall

The mechanically detectable shape is narrow enough to be worth encoding:

- a test whose name or docstring marks it as a **negative / control / matched-control** case, AND
- whose asserted value is **also reachable** by at least one other production path in the same
  module.

Surface the pair as a candidate for human judgement — it is not a decidable defect, but it is a
cheap high-yield candidate shape, and it is the specific shape that escaped five internal passes
here.

## Relationship to the existing corpus

`2026-08-27-16-006` ("Five transcribed populations reached review, and one had under-scoped its own
premise") is adjacent — both are about a check whose premise is narrower than it appears — but the
mechanism differs. That lesson is about a *transcribed population*; this is about a *control that
cannot discriminate*. Filing separately rather than merging, because the surfacer each implies is
different.
