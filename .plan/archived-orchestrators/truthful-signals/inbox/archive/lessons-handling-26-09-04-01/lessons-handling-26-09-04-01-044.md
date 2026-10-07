envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:34:22Z

component=plan-marshall:persona-module-tester
category=improvement

Relayed from Token-Sheriff PLAN-08 (PR #730 / `c40963ac`).

# Candidate lesson: a new guard test relied on a cross-module convention nothing documented

**Origin signal**: Q-Gate finding, phase `4-plan`, resolution `fixed`.
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).

## Observation

The plan introduced a guard test that depended on a convention holding across module
boundaries. The convention was real and the test was correct, but the convention itself
was written down nowhere — it existed only as an emergent regularity in the existing
code. Q-Gate flagged it at `4-plan`; it was resolved in-run by documenting the
convention.

## Why it is candidate-lesson shaped

An undocumented cross-module convention is load-bearing in exactly one direction: code
that honours it keeps working, and code that does not honour it fails for a reason no
reader can look up. A guard test makes that worse in a useful way — it converts the
silent convention into a red test — but a red test citing an undocumented rule tells a
future maintainer *that* they broke something without telling them *what* rule they
broke.

Possible corrective (for the orchestrator to judge): a test that enforces a convention
spanning more than one module must land together with the written statement of that
convention, in a location the failure message can point at. "The test IS the
documentation" does not hold across a module boundary, because the reader who trips it
is by definition not working in the module the test lives in.

## Cross-plan judgement deferred

Whether this is a project-local fact about this repository's module layout or a general
rule about guard tests is the orchestrator's call, as is whether it belongs in the
architecture-hints store rather than the lessons corpus. This plan transmits the
candidate only.
