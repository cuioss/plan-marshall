envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T16:26:53Z

component=plan-marshall:phase-3-outline
category=improvement
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# A scope heuristic that counts path mentions in a spec can be fooled by the spec's own citations — and the pre-override routing input is not persisted, so the misroute is unauditable

## What happened

The planning-lane router selected the **light** lane for this plan. The operator overrode to
**deep**. The deep outline then refuted **three** claims the plan spec asserted as observed
fact (see the landing message): a wrong row count, a misdiagnosed defect (the marker text
already matched — the real cause was an unreachable `status == "pending"` guard), and a
hypothesis that was true but **four times wider** than stated.

The light lane, by construction, would not have discovered any of them: it is the bounded-
localized-change lane and takes the spec's own account of the surface as given. The plan
would have shipped a fix for a defect it had misdiagnosed.

## What the artifacts confirm — and what they do not

**Confirmed** (`status.json` `metadata`):

```
planning_lane: deep
lane_escalated: true
escalation_trigger: cross_cutting
```

**Also confirmed** — the final `references.json` carries `scope_estimate: single_module`
and `track: complex`, and `affected_files` lists **10** paths across four skills
(`plan-retrospective`, `phase-5-execute`, `phase-6-finalize`, `ref-workflow-architecture`)
plus 4 test files. That is plainly not a surgical footprint.

**NOT confirmed by any artifact**: the *pre-override* routing input. The reported cause —
a `scope_estimate: surgical` derived from a single path token that was a boilerplate-header
citation rather than a target file — survives only in the session narrative. `references.json`
holds the post-escalation values, and `request.md` has no `scope_estimate` section at all
(its 16 sections do not include one). **The router's input at decision time is overwritten
by its output.**

That gap is itself half the lesson: an operator override of the lane router leaves no
auditable record of *what the router saw*, so a systematic misroute cannot be detected
across plans. There is no way to ask "how often does the router pick light and get
overridden, and on what input?"

## Corrective rule (two parts)

**(a) A path token appearing in a spec is not evidence that the path is in scope.** Specs
cite paths for many reasons that are not "this file will be edited": boilerplate headers,
"the shape to copy" references (this spec cites `test/_shared/_dispatch_roster.py` twice
purely as a pattern to imitate), prior-art PR references, and "confirm/refute artifact"
citations. A scope estimator that counts path mentions treats all of these as targets.
Derive scope from **deliverable-declared targets**, not from a mention count over spec prose.

**(b) Persist the routing decision's INPUT, not just its output.** Record the pre-override
`scope_estimate` / lane recommendation alongside `lane_escalated` and `escalation_trigger`,
so a misroute is auditable after the fact. `escalation_trigger: cross_cutting` tells you an
override happened; it does not tell you what the router got wrong.

## Impact

Any plan whose spec is written *about* the codebase (audit findings, retrospective follow-
ups, lesson-derived plans) rather than *at* a narrow target — i.e. most of this epic's
plans. The failure is silent and asymmetric: over-scoping costs tokens, but under-scoping
ships a fix for a misdiagnosed defect while every gate reports green, because the gates
verify the change that was made, not the diagnosis behind it.

**Note for the orchestrator's judgement**: unlike this plan's other candidates, part (a)'s
causal story rests on session narrative rather than a persisted artifact. Part (b) is
independently verified and is the reason part (a) cannot be checked. Weigh accordingly —
part (b) may be the more defensible lesson to file, with (a) as its motivating case.
