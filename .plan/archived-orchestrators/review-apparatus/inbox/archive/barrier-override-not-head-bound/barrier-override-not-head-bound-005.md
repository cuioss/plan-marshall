envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T11:42:51Z

component=plan-marshall:phase-3-outline
category=improvement
title=A spec's hypothesis about the existing population is a claim to be falsified in D1, not a premise to build on

# A spec's stated hypothesis about the existing population must be falsified, never assumed

## What happened

Plan `barrier-override-not-head-bound`'s spec carried an explicit hypothesis: *no existing
merge-gate authorization mechanism lapses on a HEAD change*. The plan therefore framed itself
as introducing HEAD-binding where none existed.

Deliverable 1's derivation found the hypothesis **partly wrong, in two directions at once**:

- **The population was 6×, not 1×.** Six merge-gate authorization mechanisms exist, not one:
  `barrier-ask-override`, `pre-merge-consent`, `red-ci-override`, `rereview-timeout-override`,
  `automatic-review-force-done`, and `final_merge_without_asking`. Four of them were NOT
  HEAD-bound — three of those four were never in the plan's framing at all.
- **One member was already bound — the counterexample.** `automatic-review-force-done`
  already captured `head_at_completion` via its step's `head_dependent: true` declaration, so
  it already lapses on HEAD change. Building on the hypothesis unchallenged would have meant
  "fixing" a mechanism that was already correct, or (worse) replacing a working binding with
  a second, competing one.
- **One member was out of class.** `final_merge_without_asking` is standing config: it
  authorizes a *policy*, not a specific tree, so HEAD-binding does not apply. Recorded with
  rationale rather than silently omitted.

The plan handled this correctly: it enumerated the population into a `## Merge-Authorization
Roster` of Markdown list rows, and pinned it with a derivation test that parses that roster
(`parse_roster_rows`), asserts non-emptiness FIRST, carries no cardinality literal, and
applies a per-member mutation guard. The lesson is that the enumeration had to happen at
all — the spec's hypothesis alone would have shipped a partial fix.

## Why it recurs

A defect report is a **sample of one**. The spec is written from that sample, so the spec's
population claim inherits the sample's blind spot. Two failure modes follow, and they are
inverses:

- **Under-count** — other members of the class exist and stay broken (here: 3 unnamed
  mechanisms).
- **Over-count** — a member is assumed broken and is already correct (here:
  `automatic-review-force-done`).

Both are invisible if the population is taken as given. This is the same family as "a
reviewer's list of call sites is a SAMPLE, not an enumeration" (CodeRabbit named 3
`write_status` callers; the real count was 14) and "volume-read-as-coverage".

## Rule

1. **Any population or negative-existence claim in a spec ("no existing X does Y", "this is
   the only site", "there are N of these") is a HYPOTHESIS. The first deliverable falsifies
   it by enumeration.** Never carry it forward as a premise.
2. **Record the enumeration as a machine-parseable artifact in the authoritative document**,
   not as a one-time finding in the plan. A derived roster survives the plan; a finding does
   not.
3. **Every member gets a disposition, including the ones needing no change.** "Already
   satisfied" and "out of class, because …" are outcomes that must be *written down* — a
   member that needs no work and is simply absent from the list is indistinguishable from a
   member that was missed.
4. **Population-derived detectors, always** — parse the roster, assert non-empty FIRST (or
   every later assertion passes vacuously against an empty parse), no cardinality literal, and
   one per-member mutation guard so the check is sensitive to each member independently.
5. **Report the delta between hypothesis and enumeration explicitly** in the landing. "The
   spec said 1, the enumeration found 6, and 1 of those was already correct" is the highest-
   value sentence the plan produces for the epic.

## Scope note for the orchestrator

Domain-invariant planning rule, aimed at the outline/D1 phase. Concrete artifact:
`phase-6-finalize/standards/branch-cleanup.md` § Merge-Authorization Roster +
`test/plan-marshall/phase-6-finalize/test_merge_authorization_roster.py`. Classification
deferred to the orchestrator.
