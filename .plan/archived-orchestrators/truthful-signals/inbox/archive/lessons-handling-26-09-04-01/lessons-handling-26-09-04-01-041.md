envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:32Z

component=plan-marshall:build-maven
category=bug

# The build wrapper's tests_run reports only the trailing Failsafe Results block, under-reporting a run that also executed 762 Surefire tests

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-18-003` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-18-003`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities`, 2026-09-08.

`plan-marshall:build-maven:maven run --command-args \"verify -pl token-sheriff-client -am\"` returned
`tests_run: 7`. The Maven log for that same invocation contains two `Results:` blocks: Surefire
reporting **762 tests**, and a trailing Failsafe block reporting **7**. The wrapper reported only the
trailing one.

The executing agent read both blocks out of the log rather than trusting the summary, which is how
the discrepancy surfaced at all.

## Impact

`tests_run` is the wrapper's own claim about how much test execution a build performed, and it
under-reports by two orders of magnitude on any module that runs both Surefire and Failsafe. Anything
downstream that reads it as a coverage or population signal — a freshness cross-check, a
retrospective's test-volume figure, a gate that treats a low count as \"barely tested\" — is reading a
number that describes the last block of the log rather than the run.

The direction matters and is worth stating exactly: the number is too SMALL, so it cannot manufacture
a false green from a run that tested nothing. The realistic harm is the inverse — a genuine 762-test
run that looks like a 7-test one, which erodes trust in the figure until nobody reads it, and that is
how a genuinely near-empty run later passes unnoticed. On this plan the same shape already appeared
from the other direction: `verify` without the integration profile reports `tests_run: 0` because
`skipITs` is on, which is accurate but reads identically to \"nothing was tested\".

## Directive

Sum every `Results:` block in the Maven log rather than parsing the last one, and report the phases
separately (`surefire_tests` / `failsafe_tests`) so a consumer can tell unit execution from
integration execution instead of inferring it from one conflated total.

Until then, do NOT quote the wrapper's `tests_run` as the number of tests a build ran. Read the log's
`Results:` blocks, and when reporting a count say which phase produced it.
