envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:40:42Z

component=plan-marshall:plan-retrospective
category=bug
title=Two retrospective checks report clean over a population they never examined
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing

# Two retrospective checks report clean over a population they never examined

## Context

The plan this was observed on exists to close the vacuity class "a rule that is green because it examined nothing". Its own retrospective produced two fresh instances of that class.

**Instance 1 — the manifest cross-check skips the rule that fired.** `check-manifest-consistency` reported:

```
tests_only_diff,skip,"rule M3 not applicable — verification_steps != [\"module-tests\"]"
```

while the manifest carries `phase_5.verification_steps: ["verify:module-tests"]` and `decision.log` 58349e records `Rule tests_only fired`. The check compares against the bare `module-tests` and the manifest stores the namespaced `verify:module-tests`, so the ONE decide-rule that actually fired is the one rule never cross-checked. The fragment then summarises `passed: 2, failed: 0, findings: 0`.

**Instance 2 — the dispatch audit's shape detector has an empty population.** `execution-context-dispatch-audit` defines `shape_violation` as "a resolve-target entry with no following `[DISPATCH]` line". This plan's `decision.log` contains **zero** `(plan-marshall:manage-config) effort resolve-target` entries across 137 lines, while `work.log` carries **25** `[DISPATCH]` lines. With an empty Surface B the detector is structurally incapable of firing, and it reports `shape_violation: 0` indistinguishably from a genuinely clean trail. The condition actually present — 25 dispatches with zero recorded resolves, i.e. every dispatch unprovenanced — has no category in the detector at all.

## Root cause

Both checks report a count without publishing the population that count was computed over. Instance 1 narrows the population to zero via a silent string-form mismatch; instance 2 inherits a population of zero from an upstream producer that never emitted. In both cases `0 findings` is rendered identically whether the check examined everything and found nothing or examined nothing at all.

## Proposed action

- `check-manifest-consistency`: normalise the `verify:` prefix on both sides before comparing, and change every `skip` verdict to carry the two values it compared so a mismatch is visible rather than inferred.
- `execution-context-dispatch-audit`: publish `resolve_target_entries_observed` alongside `shape_violation`, and treat `dispatch_lines > 0 AND resolve_entries == 0` as its own finding category (the inverse of `shape_violation`) rather than as a clean pass.
- Generally: every set-guarding detector in this skill should publish its population size next to its count, per the standing rule that a check able to return 0 from an empty population MUST report the population.

## Evidence

- aspect: manifest-decisions — `tests_only_diff,skip,"rule M3 not applicable"` against `decision.log` 58349e `Rule tests_only fired`
- aspect: execution-context-dispatch-audit — 25 `[DISPATCH]` lines, 0 `effort resolve-target` entries, `shape_violation: 0`
- source: `execution.toon` `phase_5.verification_steps[1]: verify:module-tests`
