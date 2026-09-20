envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:24Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
rank=5
source_plan=truth-166-architecture-refresh-migration-churn

# Put the absent-is-not-zero duty on build_time's producer, not only on its reader

## Context

`references/plan-efficiency.md` already carries the rule in full:

    Absent is not zero. A plan with build_count: 0 has no ledger build rows — its build
    time is UNAVAILABLE, not "no builds ran". Render totals.total_build_seconds as
    unavailable, never as 0: a 0 asserts a measurement nobody made, and it averages into
    every cross-plan roll-up as though the plan had built instantly.

But that duty is placed on the CONSUMER, while the producer still emits a bare zero.
`analyze-logs` emitted, for this plan:

    build_time:
      total_build_seconds: 0.0
      build_count: 0
      suspect_count: 0

for a plan whose SAME fragment reports 28 `pyproject_build` calls totalling 3,975,160ms,
whose folded global logs report 123 build calls totalling 11,289,620ms (51.7% of all
script time, max 1,240,550ms), and whose plan directory holds 13 `build-results` logs
including four of roughly 6.5MB each.

## Root cause

`build_time` publishes no population and no could-not-look status, so a zero from "the
change-ledger had no rows" is indistinguishable from "no builds ran". This is conspicuous
because its sibling blocks in the same fragment all do publish one: `cost_rollup` names
`population: plan_script_execution_log`, and `artifact_emission` reports
`change_attribution: unavailable` together with a `change_attribution_reason`.

## Proposed action

Have `build_time` publish the population it read (the change-ledger) and emit
`unavailable` — or omit `total_build_seconds` entirely, as `scope_creep_check` omits
`residual_count` — when the ledger carries no rows. Keep the consumer-side rule; it stops
being load-bearing once the producer is honest.

## Evidence

- aspect: log_analysis — `build_time.build_count: 0` beside
  `script_cost_rollup.ranked` showing `pyproject_build,28,3975160.0` and
  `global_log_signals.cost_rollup.ranked` showing `pyproject_build,123,11289620.0`.
- aspect: log_analysis — `slowest_scripts` lists three `pyproject_build` calls at
  987,550ms / 929,200ms / 885,320ms (16.5, 15.5 and 14.8 minutes).
- contract: `references/plan-efficiency.md` § "Build time is READ from the
  change-ledger" — states the rule, and assigns it to the reader.

## Generalizes

An honesty rule stated for the reader leaves every OTHER reader of the same field
inheriting the false zero, and readers multiply while the producer stays single. Put the
discriminator where the value is created. The cross-plan cost is named in the rule's own
text: a bare `0` averages into roll-ups as an instantaneous build.
