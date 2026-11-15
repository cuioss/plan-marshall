envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-11-03T08:18:45Z

# verdict_currency classify invalidates every head-dependent finalize verdict with `verdict_inputs_undeclared`

Source: API-Sheriff PLAN-V02-55 (`plan-v02-55-it-concurrency-and-local-image-hazard`, PR #558), phase-6-finalize. Component: `plan-marshall:phase-6-finalize` (verdict currency).

## Observation

Whenever HEAD advanced during finalize (every review-bot fix push), `verdict_currency classify` returned `invalidated` with reason `verdict_inputs_undeclared` for every head-dependent step: code-review, functional-review, finalize-step-simplify, finalize-step-security-audit, ci-verify, automatic-review and sonar-roundtrip. The delta was a single test file in each case (for example `ebdb80e6..b9f814f1`: four commits, all confined to one integration-test class). The classifier does not compare the delta against any declared inputs, because no step declares them, so it fails closed on every push.

The operator therefore had to decide by hand to carry the verdicts forward (decision log, 2026-11-02T16:48:54Z), or let the run re-fire the simplify and security-audit steps (work log, 2026-11-02T07:21:26Z: "HEAD advanced b5be2c84 -> 2aa810e2 (verdict_currency invalidated: verdict_inputs_undeclared)").

## Why it matters

Failing closed is correct while no inputs are declared, but with zero declarations the classifier can never return anything other than `invalidated`, so it adds a decision point without adding information. In a run with four review-fix rounds it turned every round into either a full re-fire of the review steps or an operator ruling.

## Suggested direction

Declare verdict inputs per head-dependent step (for example the footprint classes or path globs each verdict reads), so the classifier can return `current` when the delta lies outside them; or, until declarations exist, report `unknown` with the delta's footprint so the orchestrator can decide without a manual diff.
