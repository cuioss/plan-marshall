envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:52Z

# Candidate lesson: Red CI has no triage route: verification-feedback refuses the producer ci-verify files its findings under

- Component: plan-marshall:phase-6-finalize
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-011 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during the finalize phase of plan primitive-spi-and-validators (PR #18). Checked against the decision log of the plan.

## What happened

`ci-verify` files its findings under producer strings such as `ci-verify-policy`. `phase-6-finalize` prescribes one verification-feedback dispatch per such producer. The accept-set of verification-feedback is `build-runner, sonar, pr-comment, plugin-doctor, pr-state, finalize-feedback`; it refused the dispatch with `unknown_producer`. No per-producer triage ran for red CI.

The cause was then established by a read-only look: Sonar quality gate `new_reliability_rating=C` from one BUG java:S2789 at `PrimitiveRegistry.java:161`. The ci-verify step record was left absent so that re-entry fires the step again, and the findings stayed pending for the unified triage (producer `finalize-feedback`) after automatic-review and sonar-roundtrip had filed.

## Verification of the wording

- Confirmed by decision log ef91c1 (2026-10-09T23:07:06Z, WARNING): refusal with `unknown_producer`, the accept-set as listed, 5 `ci_policy_failure` findings at 3853d09, step record left absent.
- NOT confirmed from the decision log: that nine triage findings were resolved by hand once CI went green. The log names 5 findings at the first red run and records a second failed ci-verify at 23:40:45Z without a count. The number nine is the orchestrator's own statement.
- Note: the execution manifest does carry `ci-verify outcome=failed` entries (affba5, twice); "step record absent" refers to the phase step record, not to the manifest.

## Proposed rule

Either verification-feedback accepts the producers ci-verify writes, or ci-verify files under a producer the accept-set already holds. A step that files findings and a step that triages them must be tested against each other's producer vocabulary.

## Evidence

- Decision log ef91c1, affba5, 96775c.
