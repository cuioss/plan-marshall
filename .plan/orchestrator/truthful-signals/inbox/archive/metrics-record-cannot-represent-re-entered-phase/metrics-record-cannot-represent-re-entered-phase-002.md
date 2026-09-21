envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:02:14Z

# Candidate lesson: the vacuous-guard archetype recurred INSIDE the fix for it — twice, now with proof

**Source**: PLAN-TRUTH-055 execution + Q-Gate finding `6c64ad` (6-finalize)
**Defect class**: vacuous guard (n-th recurrence; the recurrence archetype is already in the epic)

## What is new here

The recurrence archetype "a fix for vacuous guards introduces vacuous guards" has been recorded
before as an **assertion**. This run produced an **empirical demonstration** of it, which is a
different and stronger artifact.

A guard was added in this plan to catch the failure mode "two producers agreeing by coincidence".
That guard itself could only see module-level patterns and could not see a function-local one —
so the guard was vacuous in exactly the way it was written to prevent.

The load-bearing evidence is not "we noticed it". It is this: **the old guard demonstrably stayed
GREEN while the defect it names was live in the tree.** That is a matched negative control on the
guard itself, and it converts the archetype from a claim about our habits into a measured property
of the guard.

## Why the archetype survives being named

Naming the archetype does not defeat it, because the failure is not one of attention. Writing a
guard requires choosing a population to guard over, and the vacuity is *in that choice* — it is
invisible from inside the guard, which reports a clean pass over whatever population it did
enumerate. The author of a vacuous-guard fix is in precisely the same position as the author of the
original vacuous guard, holding the same tool and making the same class of population choice.

## Candidate rule

Every set-guarding detector must be **population-derived**, and must **publish the population
size** it computed over. A check that can return 0 from an empty population must say so. This
epic already carries that rule; what this run adds is the enforcement corollary:

> A guard written to fix a vacuous guard MUST ship with a matched negative control that fails when
> the guard is removed or narrowed. Absent that control, the new guard has the same evidential
> status as the one it replaced.

The Q-Gate resolutions in this plan actually met that bar where they were caught — see
`test_deliverable_count_agrees_with_the_authoritative_extractor` (parametrized over four outlines
where the retired grammar and the section-scoped extractor genuinely disagree, each case asserting
BOTH agreement and that the retired grammar gives a different answer, so it cannot pass vacuously)
and `test_the_two_deliverable_extractors_share_one_heading_pattern` (fails if the regex is ever
compiled more than once). Those are the shape to copy.

## Suggested disposition

This is a reinforcement of a standing epic-level archetype, not a new rule. The value is the
empirical proof and the enforcement corollary. Orchestrator to decide whether it strengthens the
existing corpus entry or warrants a `arch-constraint` rule identity of its own.
