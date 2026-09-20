envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:46Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-path-gate-and-invariant-gaps` (PR #687), original message `refresh-path-gate-and-invariant-gaps-002.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: a deliberate negative control's red build was captured as blocking findings

## What happened

To prove the JaCoCo coverage gate actually binds, the run deliberately
misspelled an `include` pattern — a textbook negative control: break the input,
confirm the guard goes red, restore. The gate did go red, which is exactly the
result that proves the guard works.

The findings pipeline captured that red build as **9 `build-error` findings and
7 `test-failure` findings**. Both are blocking types. Had they not been noticed
and resolved by hand, they would have held the finalize boundary open against
the `pending_findings_blocking_count` invariant.

So: the evidence that a guard WORKS was recorded, verbatim, as evidence that
the code is broken. The polarity was inverted at the capture layer.

## Root cause

Findings capture is keyed on the *observable* (a non-zero build exit, parsed
error/failure lines) with no channel for the *intent* of the invocation. A
negative control and a genuine regression are byte-identical at that layer —
they differ only in whether the operator expected red. Because nothing carries
that expectation, the capture layer defaults every red to "regression", which
is the safe default for an unannotated build and the wrong one here.

Note this is the mirror image of the discriminator defect in the sibling
candidate-lesson: there a surface asserted a verification it never did; here a
surface recorded a verification it DID perform under the wrong sign. Same root
family — a signal whose meaning is decided somewhere other than where its
evidence is produced.

## The reusable rule

> A negative control is an experiment whose SUCCESS criterion is a red build.
> Any pipeline that harvests findings from build output needs an explicit
> expected-red mode; without one, running a negative control necessarily
> pollutes the blocking-findings store, and the only remedies are "do not run
> negative controls" or "clean up by hand afterwards" — both bad.

Matched positive/negative controls are already prescribed by
`persona-module-tester` as the way to prove a fixture-level guard binds. That
prescription and the findings pipeline are currently in tension: following the
testing standard damages the finalize gate. Closing that tension is the
actionable part.

## Candidate remediations (for orchestrator judgement)

1. An explicit expected-red marker on the build invocation that routes parsed
   errors/failures to a non-blocking `insight`/`tip` record (or suppresses
   capture entirely) instead of `build-error` / `test-failure`.
2. Failing that, a documented post-control cleanup obligation — resolve the
   control's findings as `rejected` with the control named as the reason — so
   the pollution is at least bounded and auditable rather than discovered at
   the gate.

Option 1 is preferable: option 2 depends on the operator remembering, which is
the same class of guarantee this lesson exists to remove.
