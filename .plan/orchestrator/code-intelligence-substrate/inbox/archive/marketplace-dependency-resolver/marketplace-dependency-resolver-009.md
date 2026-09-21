envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:18:13Z

component=plan-marshall:plan-marshall-plugin
category=bug
title=A hidden identity gate makes a non-emptiness assertion fail for the wrong reason unless the precondition fails first

# A hidden identity gate makes a non-emptiness assertion fail for the wrong reason unless the precondition fails first

## What happened

Deliverable D4 asserts that `architecture impact` returns a **non-empty** result over
the marketplace. That assertion is only reachable for **the plan-marshall marketplace
specifically**: `plugin_discover` early-returns `[]` unless `marketplace.json`'s
`name` is exactly `plan-marshall`.

So the test has two independent ways to go red:

1. the derivation resolvers genuinely produce no edges — the defect the test exists
   to catch, or
2. the fixture's `marketplace.json` does not carry the `plan-marshall` name — a
   fixture-setup problem with nothing to do with resolvers.

Both surface as the **same** failure: "expected non-empty, got empty". The
assertion's message points at the resolvers in both cases, so case 2 sends the
reader to debug code that is working.

## The generalisable shape

A **hidden identity gate** — an early return keyed on an environment property the
test never mentions — converts every downstream assertion into a conditional whose
condition is invisible at the assertion site. The assertion's failure message
describes the wrong cause with full confidence.

This is more corrosive than a flaky test. A flaky test is distrusted. A test that
fails with a confident and wrong explanation is *believed*, and the time goes into
the wrong component.

## Corrective rule

**A hidden precondition must be asserted separately, and it must fail first.**

Add an explicit precondition assertion ahead of the substantive one, phrased in the
vocabulary of the precondition itself — "this test requires a marketplace whose
`marketplace.json` name is `plan-marshall`; discovery early-returns otherwise". When
the fixture is wrong, that check goes red and names the fixture. Only when it passes
does the non-emptiness assertion carry information about resolvers.

The general form: **for every early return that can silently empty a result set, the
consuming test asserts the early return did not fire, before asserting anything about
the result.** Two failure causes must have two failure messages.

## Corrective rule for the gate itself

An identity gate that returns `[]` is indistinguishable from a genuine empty result
at the call site. Where the API permits, prefer a discriminated outcome ("not
applicable" vs "applicable, zero results") over an empty list that means both. That
is the same discriminator this epic already needed for absent-vs-empty optional
output sections.

## Disposition in this plan

The fixture requirement was made an explicit, separately-failing precondition. It is
no longer possible for a fixture-naming mistake to be reported as a resolver defect.
