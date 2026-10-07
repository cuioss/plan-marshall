envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:34:22Z

component=plan-marshall:build-maven
category=bug

⛔ **FOLD REQUEST — recurrence of `-013` and `-026`** (whole-tree widening by argument removal is unsound for a Maven reactor). This is the **fourth** plan in this repository to have both pre-push gate arms degrade for the same reason. Please fold; the recurrence count is the signal.

Relayed from Token-Sheriff PLAN-08 (PR #730 / `c40963ac`). ⚠ Note the plan recorded the arms as **degraded, not clean green**, and covered the dimension via whole-tree `verify` instead — the honest disposition.

# Candidate lesson: two pre-push gate arms degraded because bare `test-compile` cannot run in this project

**Origin signal**: run observation offered by the orchestrator for judgement (not one of the three counted signals).
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).

## Observation

The bare `test-compile` goal cannot run in this project. Both shapes fail on the
unpackaged validation test-jar:

- whole-tree `test-compile` — fails
- module-scoped-client `test-compile` — fails

`build-maven` has no `resolve-test-scope` verb, so there is no supported way to get the
test-scope classpath resolved short of a fuller build. The consequence was concrete:
**two pre-push gate arms degraded** — they did not fail loudly, they ran in a reduced
form.

## Why it is candidate-lesson shaped

A degraded gate arm is the dangerous shape here. A gate that *fails* stops the run and
gets fixed; a gate that *degrades* still reports a verdict, and that verdict is computed
over a smaller surface than the gate's name claims. Two arms degrading at once means the
pre-push gate's green was narrower than it read, on a PR that then merged.

This is adjacent to existing knowledge about this project's test-jar packaging (the
module-scoped `-pl/-am` form works where the widened whole-tree form cannot resolve the
validation test-jar). What is new is the *gate-level* consequence rather than the
build-invocation-level one.

Possible correctives (for the orchestrator to judge):
1. A gate arm that cannot run its intended command should report `indeterminate` and say
   so in the gate's own verdict, not silently reduce and pass. An unobservable check is
   not a passing check.
2. If test-scope resolution is genuinely needed by gate arms, the absence of a
   `resolve-test-scope` verb on `build-maven` is a capability gap worth naming as an
   owed follow-up rather than routed around per-plan.

## Cross-plan judgement deferred

Whether this is a project-local architecture fact (belongs in the hints store for this
repository's build module), a `build-maven` capability gap, or a general rule about
degraded gate arms is the orchestrator's call. This plan transmits the candidate only.
