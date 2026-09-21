envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:16:33Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
title=Stale count-prose expressed as an exclusivity phrase escapes a numeral-shaped detector

# Stale count-prose expressed as an exclusivity phrase escapes a numeral-shaped detector

## What happened

`verification-feedback.md` line 185 asserts that **"only the security-audit pilot
declares one"** implementor of the verify extension point. `ext-point-verify.md` now
declares **four** implementors. The prose has been false since the second
implementor landed; it is pre-existing on `main` and was not introduced by the plan
that found it.

## Why this is a detector gap, not just an instance

The marketplace already has a **stale count-prose** candidate class in
`ext-self-review-plan-marshall`. A stale count claim nevertheless survived on `main`
in a document inside that detector's own domain. So the instance is evidence about
the detector, not only about the document.

The discriminating property: this count is not written as a numeral. It is written
as an **exclusivity phrase** — `only … one`. A detector that keys on digits, or on
"N implementors"-shaped strings, does not see it. The claim is quantitative; the
surface form is not.

That generalises. The same count claim can be spelled:

- `only the X declares one` / `the sole implementor`
- `a single implementor` / `just the one`
- `X is the only …` / `no other … exists`
- `currently only X` / `X alone`

Every one of these asserts a cardinality of exactly 1, and every one is invisible to
a numeral scan. Exclusivity phrasing is in fact the **most** likely form for a
cardinality-1 claim, because English prefers "the only" over "the 1". So the detector
is systematically blind to the single most common instance of the class it targets.

## Corrective rule

Extend the stale-count-prose candidate class to match **exclusivity and cardinality-1
phrasings**, not just numerals. The high-value trigger set is the closed vocabulary
`only | sole | single | alone | just the | no other | the one`, appearing in the same
sentence as a term that names an enumerable set (implementor, provider, consumer,
caller, resolver, bundle, phase, step).

Cardinality-1 claims are also the ones most likely to go stale, because "1 → 2" is
the very first change a growing extension point undergoes — and the moment a second
implementor lands, the sentence flips from true to false with no edit to the file
that carries it.

## Corollary for authors

Prefer not to state a cardinality in prose at all when the set is enumerable from a
manifest. Point at the manifest instead. A count written once and never re-derived is
a claim with a scheduled expiry date.
