envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-11-09T16:24:23Z

Routed by the API Sheriff epic `kidicap-gateway-requirements` (standing operator rule 2026-10-15: plan-marshall-related findings go to lessons-routing). Origin: plan `plan-29-upstream-inert-keys`, API Sheriff PR #586 (merged 2026-11-09, ab568dab), plan-marshall 0.1.2088. The orchestrator verified the PR and CI state, not the plan-marshall-internal claims (Q-Gate finding contents) below; treat those as the plan lane's own report.

# Candidate lesson: test removal named in the spec but not declared in the outline's Tests-to-remove format trips weakened_test

Source record: Q-Gate finding 91a07e (phase 6-finalize, rule functional-review, severity error, resolution accepted).

## What happened

The functional review's weakened_test check flagged that one assertion present at c86ee5b9 was gone from
`ConfigValidatorTest.ValidConfiguration::shouldAcceptMillisecondPrecisionTimeout`
(api-sheriff/src/test/java/de/cuioss/sheriff/gateway/config/validation/ConfigValidatorTest.java).
The removal was intended: the test exercised `readTimeoutMs`, which PLAN-29 removed by the operator's
2026-10-26 decision, and the spec lists that removal. The outline, however, never declared the removal in
the structured Tests-to-remove form the weakened_test check reads, so the check blocked and the operator had
to accept it by hand at the finalize review. All 3 deliverables and 18 criteria were otherwise graded met.

## Candidate rule

When a deliverable deletes a config key / API surface, the outline must carry every test removed with it in
the declared Tests-to-remove format, not just in spec prose. A spec-level mention is not visible to the
functional review's weakened_test gate.

## Possible corrective surfaces (for orchestrator classification)

- phase-3-outline: derive Tests-to-remove entries when a deliverable removes a key the tests reference.
- functional-review weakened_test: consult the spec's stated removals, or report the spec mention in the
  finding, so an intended removal is distinguishable from a weakened test without an operator round-trip.
