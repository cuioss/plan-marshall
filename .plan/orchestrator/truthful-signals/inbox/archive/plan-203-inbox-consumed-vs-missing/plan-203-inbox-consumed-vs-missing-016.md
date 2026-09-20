envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:23:29Z

# Prune predicate evaluates plan footprint at compose time when it is empty by construction

component: plan-marshall:manage-execution-manifest
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

At manifest-compose time (19:18:33, phase 4-plan), `decision.log` records:

```
(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted —
plan footprint is empty — no changed files to build
```

One line later:

```
(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection —
finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

PLAN-203 went on to change 8 files. The pre-push quality gate ran and was material — it is one of the
gates that would have caught a broken commit before push.

## Root cause

The prune predicate is evaluated at compose time, in phase 4-plan, **before phase 5-execute has
written a single byte**. The plan footprint is empty at that instant for every plan, unconditionally.
The message states this structural fact as a conclusion about this specific plan ("no changed files to
build"), which is the confident-zero shape this epic tracks: a zero meaning "nothing has happened yet"
rendered as a zero meaning "there is nothing to do".

The gate survived only because this project sets `finalize.qgate=always`. A project on the default
ceremony posture would silently ship an 8-file change with the pre-push quality gate pruned, and the
manifest would carry a plausible-sounding justification for the omission.

## Proposed action

1. Any prune predicate whose input is the plan footprint MUST NOT be evaluated at compose time.
   Either defer it to finalize entry (where the footprint is real) or treat an empty compose-time
   footprint as `indeterminate` and keep the step.
2. If the predicate is retained at compose time, the log message MUST state the provenance:
   "footprint not yet realized at compose time" — not "no changed files to build".
3. Audit the other prune predicates in the compose path for the same compose-time-footprint
   dependency; this was found on one step and should be treated as a sample, not an enumeration.

## Evidence

- decision.log 19:18:33 (both lines, consecutive)
- execution.toon `execution_log` — `pre-push-quality-gate` executed at 07:22:30 in 6-finalize
- `git show --name-only e82b466ee` — 8 files changed
- fragment-routing-decisions.toon — `recompose_divergence.lane_resolution_log_entries: 1`
