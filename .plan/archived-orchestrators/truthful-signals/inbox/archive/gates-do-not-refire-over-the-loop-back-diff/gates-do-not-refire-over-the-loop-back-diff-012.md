envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:11:07Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# Source-of-truth duplicate in the SKILL.md head-dependence paragraph (recorded by finalize-step-simplify, not actioned)

## Observation

`finalize-step-simplify` recorded — and did **not** action — a **source-of-truth duplicate** in the head-dependence paragraph of `phase-6-finalize/SKILL.md`, shipped by PLAN-TRUTH-001 in PR #1073.

The paragraph restates head-dependence facts that the derivation (and the registry behind it) already owns. Two independent statements of the same truth now exist, with no mechanism keeping them in agreement.

## Why this is the same defect the plan was written to remove

PLAN-TRUTH-001's entire purpose was to replace a **hand-maintained membership statement** with a **registry derivation**, precisely because the hand-maintained statement drifts. The plan then added a fresh prose statement of the same membership facts alongside the derivation it introduced.

This is the **8th-adjacent sighting** of the family (see the separate `RECURRENCE (7th sighting)` candidate-lesson): documenting a derivation tends to reintroduce, in prose, the hand-maintained artefact the derivation replaced. Prose is not exempt from the archetype — a sentence naming the members is a membership list that happens to be written in English.

## Why this belongs to `truthful-signals`

A duplicated source of truth produces a **confidently stated fact with an invisible expiry date**. The reader has no way to tell which of the two statements is current, and the prose copy will read as authoritative long after the derivation has moved on. This is exactly the "nine / three vs an eight-item list" disagreement the plan just fixed — re-seeded one layer up, in the doc that describes the fix.

## Suggested shape of the fix

1. Reduce the SKILL.md paragraph to a **pointer** at the derivation, carrying no restated membership and no restated counts.
2. Generalize: **doc prose describing a derivation must not restate the derivation's output.** It may say what the derivation computes and where it reads from; it may not say what the answer currently is.

## Not actioned

Recorded by `finalize-step-simplify` during PLAN-TRUTH-001's finalize; deliberately not actioned in-run. Handed to the epic.
