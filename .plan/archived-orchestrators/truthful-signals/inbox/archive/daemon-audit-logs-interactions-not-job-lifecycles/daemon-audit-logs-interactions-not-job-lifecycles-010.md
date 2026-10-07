envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:15Z

component=plan-marshall:manage-execution-manifest
category=bug
bundle=plan-marshall

# Two prune predicates in one compose run disagreed about whether the plan has a footprint

## What was observed

Within a single `manage-execution-manifest compose` run, one second apart, the decision
log records two mutually contradictory readings of the same plan's footprint:

```
[13:14:37] pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
[13:14:37] finalize-step-simplify  omitted — change_type=verification affected_files_count=9
```

The first predicate read the footprint as **0 files**. The second, in the same run, read
it as **9 files**. Both fired; neither is aware of the other.

The quality-gate omission was silently rescued a few lines later by an unrelated rule:

```
[13:14:37] ceremony_finalize selection — finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

So the plan DID run its pre-push quality gate — by luck of an `always` setting, not
because the prune was correct.

## Why it matters to this epic

Two defects stacked, and the second hid the first.

1. **The prune predicate is structurally vacuous.** `compose` runs in phase-4-plan, before
   phase-5-execute has changed a single file. A live-diff-derived footprint at that moment
   is empty *for every plan that has ever existed*. "Plan footprint is empty — no changed
   files to build" is not a fact about this plan; it is a fact about when the predicate
   runs. This is the project's recurring **vacuous-guard** archetype (now at least the
   fifth instance, and this one is load-bearing on a build gate).

2. **A rescue turned a wrong decision into an invisible one.** Because `finalize.qgate=always`
   re-added the step, the vacuous prune produced no observable symptom. With any other
   qgate setting, this plan would have pushed without a pre-push quality gate and nothing
   in the run would have said so. A guard that is only correct because a different rule
   overrides it is not a working guard.

Also note the third disagreement in the same block: the pre-filter read
`change_type=verification`, while `status.metadata.change_type` is `enhancement`. Three
readings of plan-scoped facts, three answers, one compose run.

## Proposed action

Consolidate onto a single footprint oracle for the whole compose pass, and make its
answer three-valued rather than two-valued: `empty` / `non-empty` / **`not-yet-known`**.
A predicate that needs a realized footprint but runs before execute MUST receive
`not-yet-known` and MUST NOT prune on it — the fail-closed direction is to KEEP the step.

The declared `affected_files` (9 here) is the only footprint estimate that exists at
compose time and is what the simplify gate already uses; the quality-gate prune should
read the same source or be deferred.

This connects directly to the epic's standing PLAN-35 item (build/no-build oracle
consolidation, `build_map` = THE oracle) — this is a concrete, reproduced instance of the
same class and should be folded into that plan's evidence rather than filed twice.

## Evidence

- `execution.toon` + `logs/decision.log` entries at 2026-07-28T13:14:37Z (all quoted above)
- `status.metadata.change_type = enhancement` vs the pre-filter's `change_type=verification`
- The retrospective's `manifest-decisions` aspect fragment (all 21 compose decision entries)
