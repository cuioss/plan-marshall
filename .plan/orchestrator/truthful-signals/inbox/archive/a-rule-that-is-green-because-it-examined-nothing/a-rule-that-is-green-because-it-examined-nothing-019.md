envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:55:02Z

component=pm-dev-java:arch-gate-java
category=bug
title=The plan's own anti-vacuity fixture asserted pass/fail only — reproducing the defect it was written to close
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=pr-comment 3a58b1 (PR #1115, coderabbitai, resolution=fixed, remediated by TASK-005)

# The plan's own anti-vacuity fixture asserted pass/fail only — reproducing the defect it was written to close

## Context

This plan exists to close a vacuous-green class: an ArchUnit rule that examined nothing passes, indistinguishably from one that examined a real population. Its deliverable was a pairing requirement — a hand-written `ArchCondition` MUST also be exercised in the positive rule form against the same deliberately non-compliant fixture.

CodeRabbit's review made two corrections, and the second is the load-bearing one:

1. **Scope.** The trap was described as the behaviour of hand-written `ArchCondition`s generally, but it holds only for the **violated-only event shape**. A condition that also emits `satisfied(...)` for compliant items has those flipped into violations under `noClasses().should(...)`, so the rule fails loudly rather than passing vacuously. The premise was carried implicitly ("the compliant items produced no events to flip") but never named as a scope limit.
2. **The pairing test asserted only pass/fail.** Asserting the outcome alone **cannot distinguish a condition that reported no events from one that reported correctly-polarised events.** That is the same examined-nothing-reads-as-green failure the negative-control obligation exists to close.

## Root cause

Point 2 is the recurrence worth recording: **the plan reproduced its own target defect inside its own remedy.** The remedy for "a green that proves nothing was examined" was itself specified as a green that proves nothing about what was examined. A pass/fail assertion over a fixture is a strictly weaker signal than an assertion over the fixture's observed events, and the gap is invisible because the test passes either way.

This is the archetype the epic already tracks — a plan that fixes a defect class reproducing that class in the fix (previously observed on PLAN-86 and PLAN-10). It is now confirmed for a third distinct plan, which argues the archetype deserves a standing pre-submission check rather than per-plan vigilance.

## Proposed action

- **Standing self-review question for any plan whose subject is a verification-quality defect**: *does the remedy this plan ships satisfy the property it demands of others?* Applied here it would have asked "does the pairing requirement's assertion distinguish examined-nothing from examined-and-compliant?" and answered no.
- **Domain-specific**: an anti-vacuity fixture must assert the *observed evidence* (event polarity, count, matched population size), never only the terminal verdict. The verdict is exactly the signal the defect corrupts.
- Generalise to the negative-control obligation itself: "ships one deliberately non-compliant fixture proving the rule can go red" should read "…and asserts the concrete evidence the rule produced, not only that it went red".

## Resolution in this run

TASK-005 scoped the trap to the violated-only event shape and strengthened the pairing requirement to assert concrete event polarity alongside the outcome. Landed as a follow-up commit on the PR branch (`f362638a`).

## Evidence

- PR #1115 inline comment `3a58b1` by `coderabbitai` at `marketplace/bundles/pm-dev-java/skills/arch-gate-java/SKILL.md:49`, reviewed commit `9f3c4755`, disposition `fixed`.
- The comment was grounded in ArchUnit upstream behaviour (TNG/ArchUnit issues 234, 550, 1310) — the correction required domain knowledge outside the repository, which is why three internal self-review iterations did not surface it.
