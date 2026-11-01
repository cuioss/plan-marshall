envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-01T20:42:34Z

# The Maven log parser files a `test-failure` finding for a passing Surefire summary line

Severity: **high (operator ruling, 2026-11-01 sweep)**. Bundle: `plan-marshall` (`build-maven` log parser).
Source: 1 lesson from the API-Sheriff checkout, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/API-Sheriff/2026-10-12-07-015.md`. Not re-verified at HEAD.

## Observed (plan-25, PR #408)

Twice in one plan the parser filed a `test-failure` finding for `Tests run: 10, Failures: 0, Errors: 0, Skipped: 1 ... -- in Awaits`. Both findings (e6b5d8, bab3b4) were triaged `accepted` as false positives with no code change; the recurrence count of the tuple (module `maven`, class `test failure [test_failure]`, disposition `accepted`) reached the `preference_min_recurrence` of 2.

## Ask

A Surefire class summary with `Failures: 0` and `Errors: 0` is a pass even when `Skipped` is above zero. Check the parser at HEAD against that line shape and add a fixture for it.

Related, archived `medium` and not filed: `2026-10-12-07-006` (`-Dtest=A+B` matches nothing and passes with zero tests; the planning step stamped the wrong form) — same surface, so worth a look in the same pass.
