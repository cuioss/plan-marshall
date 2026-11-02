envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T11:19:37Z

# jest-testing: silence captured console output with `--silent`, not a custom stubbing setup

Severity: low. Domain content, filed under RULING 2026-10-09 (operator-confirmed for this sweep); may be discarded under the `live-blockers` FOCUS RULE.
Bundle: `pm-dev-frontend` (jest-testing).

## Source

nifi-extensions `2026-06-14-21-001`, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-02/nifi-extensions/`.

## Observation

To stop Jest console output cluttering the Maven-driven build, a plan added a global setup file plus `beforeEach` hooks stubbing `console.*` and a regression test asserting the stubs. A review bot flagged it as over-engineered and harmful to local debugging, because it hides errors. Jest's built-in `--silent` in the build script does the same without the cost.

## Ground truth (c431a8193)

No jest-testing SKILL.md or standard (`test-fundamentals.md`, `mocking-async.md`, `dom-component-testing.md`) mentions `console` or `silent`.

## What to consider

Add a short rule: use `--silent` (or reporter config) in build scripts for console noise; do not stub `console` globally in test setup.
