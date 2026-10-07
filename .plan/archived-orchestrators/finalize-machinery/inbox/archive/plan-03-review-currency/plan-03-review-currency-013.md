envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T19:30:04Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-17
bundle=plan-marshall

# Dispatch roster should carry each step's prompt skills

Every dispatched finalize step forces the orchestrator to choose the
prompt `skills[]` by reading step docs ad hoc — pure guesswork with no
contract to check it against. A wrong set is silent until a leaf misses a
capability mid-run.

## Proposal

Add a skills column to the dispatch-inline-split roster (the single source
of truth for the dispatched/inline split), naming each dispatched step's
prompt skill set. Pin it with the same test family that pins the roster
closure, so a new step without a declared skill set fails the build
instead of reaching dispatch unscoped.

## Evidence

Plan plan-03-review-currency: seven dispatched finalize steps, each
requiring a separate doc read to assemble `skills[]`
(automatic-review needed eight; plugin-doctor three; self-review five).
All guesses held, but none was checkable.
