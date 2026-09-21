envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T11:42:23Z

component=plan-marshall:ref-workflow-architecture
category=bug
title=A declared output-contract field with no emitter is a producerless row - declare and emit in the same edit

# A declared-but-never-emitted `display_detail` is a producerless contract row

## What happened

Plan `barrier-override-not-head-bound`'s pre-submission self-review (commit `d64379`) found
a `display_detail` that the artifact **declared** as part of the step's output contract and
that **no code path ever emitted**. The contract row existed; the producer did not.

The consequence is specific and quiet: `mark-step-done --display-detail` is what the
finalize output-template renderer surfaces to the operator. A declared-but-unemitted field
renders the `<missing display_detail>` placeholder and forces a `[FAILED]` headline — so the
step reports as broken for a reason unrelated to whether it worked. The contract advertised
a signal that never arrives.

## Why it recurs

Declaring a field and emitting it are two edits in two places, and the declaration is the one
that gets written first (it is part of designing the contract). Nothing fails when the second
edit is skipped: the declaration is prose or schema, the omission is silence, and the
consuming renderer degrades to a placeholder rather than an error. Reviews read the
declaration and treat it as evidence of the behaviour it describes — the
"defending-documentation" / "vacuous-authority" shape.

This is the same archetype as the `dispatch_boundaries` producerless row handed over at the
test-suite-quality close: **a schema row whose producer does not exist**. It has now recurred
across at least two independent surfaces, which makes it a structural gap rather than an
incident.

## Rule

1. **Declaring a contract field and emitting it are ONE edit, not two.** A field added to an
   output contract without the emitting call site in the same change is incomplete work, in
   the same way a `[DISPATCH]` log line without its spawn is a contract violation.
2. **Every declared field needs a named producer.** When reviewing a contract, ask of each
   row: *which call site writes this?* A row that cannot be answered is producerless.
3. **Prefer a detector over a convention.** A producerless-row check is deterministic and
   population-derivable: parse the declared field set from the contract document, then assert
   each name appears at an emitting call site. This is the same shape as the roster-derivation
   tests (`parse_roster_rows` + per-member mutation guard) already used in this repo — assert
   non-emptiness FIRST so the check cannot pass vacuously.
4. **Placeholder-on-absence is a smell, not a safety net.** A consumer that substitutes
   `<missing X>` converts a producer gap into a cosmetic-looking output. Make the absence
   loud at the producing side rather than tolerable at the consuming side.

## Scope note for the orchestrator

Second observed instance of the producerless-row archetype (first: `dispatch_boundaries`).
The concrete site here is a `display_detail` declaration in this plan's own edits to
`phase-6-finalize`. The generalisable ask — a deterministic producerless-row detector over
declared contract fields — is larger than one plan and is a candidate for its own staged
plan. Classification deferred to the orchestrator.
