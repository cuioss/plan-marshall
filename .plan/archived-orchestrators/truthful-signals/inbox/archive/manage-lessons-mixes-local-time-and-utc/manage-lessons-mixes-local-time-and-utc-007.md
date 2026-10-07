envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:07:12Z

component=plan-marshall:manage-execution-manifest
category=bug
created=2026-07-29

# Manifest compose drops the pre-push build gate on a footprint predicate that is always empty at compose time

`decision.log` for this plan records, in the same compose run, two entries that contradict each other:

```
[14:02:35] (manage-execution-manifest:compose) pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
[14:02:35] (manage-execution-manifest:compose) ceremony_finalize selection — finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

The gate was dropped for "empty footprint" and then re-added only because this project's config sets `finalize.qgate=always`.

## Why the predicate cannot ever be false

Compose runs in **phase-4-plan**. Worktree materialization is **deferred to phase-5-execute Step 2.5** — this plan's own `decision.log` records that deferral at plan-init (`2b2fef`: "materialization deferred to phase-5-execute Step 2.5"), and `work.log` confirms the worktree metadata was not written until 14:11, nine minutes *after* the 14:02 compose.

So at compose time there is no worktree, therefore no diff, therefore the footprint the predicate reads is empty **for every plan, always**. The guard is vacuous: it fires unconditionally, and its stated rationale ("no changed files to build") is never a measurement of anything.

Note that a non-empty declared footprint *did* exist at compose time — `references.json` carried five `affected_files` written at outline (13:45). The predicate is not reading the source that had the answer.

## Solution

Either:

- evaluate the build-gate predicate against the **declared** footprint (`references.json.affected_files`) which exists at compose time; or
- defer the predicate to a point where the realized footprint exists; or
- remove the predicate and let ceremony/config own the decision outright.

Whichever is chosen, a predicate whose input is structurally absent at its call site must not emit a decision-log line asserting a measured cause.

## Impact

Projects that do **not** set `finalize.qgate=always` silently lose their pre-push quality gate on every plan, with a decision-log entry that reads like a justified, measured optimisation. This is the vacuous-guard archetype again (now well past n=5), in its most dangerous form: the guard removes a *verification* step, and the rationale it logs is the thing that makes the removal look reviewed.
