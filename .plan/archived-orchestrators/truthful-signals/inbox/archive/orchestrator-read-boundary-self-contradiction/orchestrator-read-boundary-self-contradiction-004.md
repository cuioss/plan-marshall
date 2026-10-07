envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:10:01Z

component=plan-marshall:phase-3-outline
category=anti-pattern
created=2026-07-28
bundle=plan-marshall

# A deliverable that DECLARES a survey scope must RUN that survey before affected_files is frozen

## What happened

Q-Gate finding `13e1ce` (severity **error**) at `3-outline`.

Deliverable 2 of PR #1040 declared a survey scope that explicitly included
`doc/**/*.adoc`, and stated that *any hit beyond the two named files is in scope and
corrected in this same deliverable*. But its `affected_files` listed only those two
named files. Nobody had actually run the declared sweep.

Running it at Q-Gate time surfaced a real, live third restatement:
`doc/concepts/orchestration.adoc:31` stated verbatim the same read prohibition D1 was
deleting from `orchestration-model.md:91`. That path appeared in **no** deliverable's
`affected_files` and was absent from the files-expected-to-mutate set — so the
retrospective's `affected_files_recall` check could never have seen it. The plan was on
track to ship claiming "no document contradicts the standard" while a concept doc still
stated the deleted prohibition.

The outline was also **internally contradictory** about its own boundary: the request's
Constraints section limited the change to two orchestrator skill docs plus one test
(which excludes `doc/`), while D2's survey scope committed to correcting any `doc/` hit.
Both statements were in the same outline.

## Solution

**Rule:** a declared-but-unrun sweep is a promise no downstream verification can check.
`affected_files` is the only handle the recall check has; a file the sweep would have
found but that nobody enumerated is invisible to every gate after the outline. So:

1. **Run the declared sweep at outline time**, before freezing `affected_files`, and
   enumerate the result — including hits outside the request's stated constraints.
2. If a hit falls outside the request's Constraints section, that is a **scope
   contradiction to resolve explicitly**, not a silent drop. Either widen the constraint
   with a recorded authorization (what happened here — an operator resolution, plus a
   "Scope-widened" paragraph in the Overview recording the authorized departure), or
   narrow the declared survey scope and record the un-swept surface as a **deliberate
   documented exclusion with rationale**.
3. Never leave the pair `{declared scope = wide, affected_files = narrow}` unreconciled.
   That pair is the signature.

**Adjacent instance from the same run** (`e082e2`): D1 asserted "verify the anchor
`#carve-outs` still resolves for the **four** in-repo links that target it" — a
repo-wide sweep returned exactly **two**. A count claim in an outline is a verifiable
factual assertion; an unverified one sends the implementer hunting for links that do not
exist. Corrective adopted: name each site explicitly *and* instruct a fresh sweep at
implementation time rather than trusting the recorded count, with any additional hit
declared in-scope for the same treatment.

## Impact

Directly on-theme for `truthful-signals`: "affected_files is complete" is a confident
signal, and the unrun sweep is the caveat it hides. The failure is invisible at the
outline site — the deliverable *reads* thorough precisely because it declares the wide
scope.

Two structural leverage points:

- **`phase-3-outline` validator**: when a deliverable declares a survey scope in prose,
  flag the case where `affected_files` was not produced by running it. A declared scope
  that names a glob is machine-comparable against the enumerated file list.
- **Request-vs-outline scope contradiction** is its own detectable pair: the request's
  Constraints section and a deliverable's declared survey scope disagreeing is a
  mechanical check, and here it was the leading indicator of the missed file.

Sibling lesson (same run, same root gap, different rule): *a regression detector's
population must not be narrower than the fix set's population*. That one governs the
guard; this one governs the fix set the guard is measured against. Operator resolution
`137ac5` resolved both together and is the record of why the pairing matters.
