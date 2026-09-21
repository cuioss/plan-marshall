envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:38Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=medium
rank=8
source_plan=truth-166-architecture-refresh-migration-churn

# Require an escalation to quote the resolved limit and the call that returned it

## Context

An operator escalation was raised during finalize stating:

    The loop-back limit of 3 is spent on the self-review rounds, so the gate will refuse
    this one.

The operator answered "Raise the limit, run the fixes (recommended)". The resolved ceiling
was already **14**: `manage-config plan phase-6-finalize get` returns
`max_iterations: 14`, and `.plan/marshal.json` is byte-identical between the plan's
`4-plan` baseline commit `7a028157` and `HEAD` — so the value predates the self-review
rounds and the operator's decision changed no configuration. The plan finished at
`loop_back_iteration: 6`, well inside 14.

`3` is the documented DEFAULT, which is where the figure came from.

## Root cause

The ceiling was recalled from documentation rather than read from the resolver, and the
escalation was built on the recalled value without quoting a source. The run's own
decision log carries the eventual correction — "iteration 5 of `max_iterations=14` per
correction `4f3cdd`" — so the value was available throughout; it was one call away.

## Proposed action

Require that any escalation whose premise is a configured limit quote **both** the
resolved value and the call that produced it, e.g. "max_iterations=14 per `manage-config
plan phase-6-finalize get`". This makes recalling a documented default structurally
visible inside the escalation text itself: a premise with no source call is refusable on
sight, by the author as much as by the operator.

## Evidence

- `manage-config plan phase-6-finalize get` → `max_iterations: 14`.
- `git diff --stat 7a028157 HEAD -- .plan/marshal.json` → empty, so the ceiling was 14
  before the rounds began and the "Raise the limit" decision altered nothing.
- `status.metadata.loop_back_iteration: "6"` — the run never approached 14.
- decision.log — "iteration 5 of max_iterations=14 per correction 4f3cdd".

## Adds to the known archetype

This is a recurrence of the read-it-from-the-resolver family already in the corpus, and is
proposed **only** for the remedy it adds. The cost here was not a wrong action but a spent
operator interrupt on a constraint that did not exist — a failure mode the existing
archetype does not name, because recalling a stale value usually shows up as a wrong
result rather than as an unnecessary question. Requiring the source call in the escalation
text is the cheapest available guard, and it fails closed.
