envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:17:37Z

component=plan-marshall:persona-module-tester
category=anti-pattern
title=A deliverable's proof asserted exclusivity the design never promised, because it was written from the narrative

# A deliverable's proof asserted exclusivity the design never promised, because it was written from the narrative

## What happened

Deliverable D4 was to prove that the newly-added **python-import derivation
resolver** contributes to the architecture impact graph. The obvious assertion — and
the one first written — was:

> some edge has `producers == [python]`

It can never hold. Every module pair the python import-join derives is **also**
derived by the markdown resolver. The python resolver never produces an edge
**alone**. The assertion was not merely unsatisfied by the current data; it is
unsatisfiable by the design.

## Why the wrong assertion was the natural one

The assertion was written from the **deliverable's narrative**, not from the
design's guarantees. The narrative is "we added a python resolver, so python edges
should now appear" — and "python edges" quietly becomes "edges that only python
found". That slide from *contributes* to *contributes uniquely* is invisible in
prose and load-bearing in an assertion.

Nothing in the design ever promised uniqueness. A **redundant producer is still a
producer**: the resolver's value is corroboration and coverage under a different
input shape, not exclusive discovery. The narrative implied an exclusivity claim the
component was never built to satisfy.

## The delicate part — which side was wrong

A failing new test on a new component is normally evidence the component is
incomplete. Here it was evidence the **claim** was wrong. Getting that call right is
the whole lesson, and it needs a proof, not a preference:

- **Fix the component** when the asserted property is one the design intends to
  guarantee and currently does not.
- **Fix the assertion** when the asserted property is one the design **never
  intended** — and you can demonstrate why. Here: every pair the import join yields
  is structurally also a markdown-derivable pair, so exclusivity is precluded, not
  merely absent.

The failure mode to avoid is weakening an assertion because it is red. The
discriminator is whether you can state the *structural reason* the property cannot
hold. If you can only say "it doesn't hold right now", the component is the
suspect — not the test.

## What the rewrite asserted instead

Three properties that are actually true and actually falsifiable:

1. the python resolver is discovered and runs,
2. the edges it derives are present in the graph (with `python` among their
   producers),
3. its provenance is recorded alongside the markdown producer rather than
   overwriting or being overwritten by it.

Each of these fails for a distinct real defect. The original assertion failed for no
real defect at all — it could only ever have been made green by distorting the
design.

## Corrective rule

Derive a deliverable's proof from the **design's stated guarantees**, not from the
deliverable's narrative sentence. Before writing the assertion, name the concrete
defect that would make it fail. If the honest answer is "nothing — it just cannot be
true", the assertion is testing the narrative, not the system.
