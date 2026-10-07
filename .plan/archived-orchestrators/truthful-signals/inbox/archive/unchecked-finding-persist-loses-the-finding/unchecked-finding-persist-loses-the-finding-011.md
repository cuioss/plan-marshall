envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T17:25:08Z

component=plan-marshall:phase-3-outline
category=improvement
bundle=plan-marshall
created=2026-07-28

# scope_estimate token/time budget anchors don't distinguish honest gate-driven scope growth from inefficiency

## Context

This plan's request declared a HYPOTHESIS (5 candidate persist call sites) and its own D1 gate
explicitly required verifying that hypothesis against the implementing source before scoping D2.
The outline's first Q-Gate pass correctly flagged the initial outline as under-scoped; the
revision pass ran a population sweep and found 10 real production persist sites (not 5), 2 of
them live-broken. This is exactly the request's own verify-first clause working as designed —
but the plan still carried `scope_estimate: single_module`, and the plan-efficiency retrospective
aspect found the plan blew BOTH the single_module+bug_fix warning anchor (800K tokens/60min) and
the error anchor (1.3M tokens/90min) — landing at ~3.14M tokens / ~4h54m wall-clock, more than
2x the error anchor on tokens alone.

## Root cause

`scope_estimate` is set once, early (at 2-refine), from a coarse file/module count, and has no
mechanism to account for a LATER, deliberately-designed gate (D1 in this plan's own request) that
may legitimately discover 2x the initially-hypothesized footprint. The efficiency anchors then
grade the whole plan against the STALE initial estimate, making a request's own honest
verify-before-scope discipline look like inefficiency in the retrospective.

## Proposed action

Consider re-deriving `scope_estimate` (or recording a secondary "revised_scope_estimate") when a
Q-Gate-triggered outline revision materially changes the declared deliverable/site count, so
`plan-efficiency`'s anchor lookup grades against the scope that was ACTUALLY executed rather than
the pre-verification guess. Alternatively, have `plan-efficiency` itself detect an outline
revision-pass entry in `decision.log` and note the anchor comparison as "graded against
pre-revision estimate" rather than presenting the overrun as unqualified.

## Evidence

- aspect: plan-efficiency — 2 [BUDGET] error-severity findings, full plan:
  unchecked-finding-persist-loses-the-finding, PR #1038
- decision.log:17,25-26 — Q-Gate flagged "scope under-coverage", revision "population sweep
  derived 10 production persist sites" (vs the request's hypothesized 5)
