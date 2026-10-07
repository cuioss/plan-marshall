envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T06:10:48Z

component=plan-marshall:manage-references
category=bug

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-02
(`inherited-build-config-verification-depth`, merged as PR #714 / `7482cf18`).
bundle=plan-marshall

# The scope-creep guard never ran on any task: references.json carries no plan_creation_sha

## Observation

Every phase-5 task execution in this plan returned `could_not_look` /
`no_baseline_sha` from the scope-creep guard, because `references.json` carries
no `plan_creation_sha`. No scope comparison was performed at any point in the
plan, on any task.

The guard reported its absent measurement honestly — this is not a silent
failure, and the `could_not_look` discriminator did its job. But an honest
`could_not_look` returned on 100% of invocations is operationally identical to
having no guard at all, and nothing in the pipeline escalated that.

## The generalisable rule

A guard whose baseline is captured by a *different* phase than the one that
consumes it will silently degrade to a permanent no-op whenever that capture is
missed. The `could_not_look` return is the correct per-invocation answer and the
wrong aggregate answer: nobody is watching the rate.

## Suggested corrective action

Two independent fixes, both worth doing:

1. **Capture the baseline where it is cheap and certain.** `plan_creation_sha`
   should be written into `references.json` at `phase-1-init`, at the same
   moment the plan directory is created and HEAD is trivially available. A plan
   that reached phase 5 without one indicates the capture point is wrong, not
   that the plan is unusual.
2. **Escalate a uniformly-unobservable guard.** When a guard returns
   `could_not_look` for every task in a phase, that is a finding in its own
   right — surface it at the phase boundary rather than letting N identical
   honest non-answers add up to zero coverage nobody noticed.

## Impact

Every plan whose `references.json` predates or misses the `plan_creation_sha`
write runs its entire execution phase with scope-creep detection disabled, while
each individual step's output looks correct.

## ⚠ Recurrence note added by the relaying orchestrator

This is the **second consecutive plan** in this epic to run its entire execution phase with the
scope-creep guard disabled. PLAN-01 (`pre-commit-gate-truthfulness`, PR #713) returned
`could_not_look` on all **ten** of its tasks for the same reason, and its landing named the one
genuine out-of-footprint edit the guard would have caught (`RefreshTestSupport.java`, a test
double migrated to satisfy a narrowed contract).

So the aggregate is now 2 plans / 100% of tasks / 0 scope comparisons performed, with one known
missed detection. That strengthens the second suggested corrective action specifically: the
per-invocation `could_not_look` is the right answer every time and the wrong aggregate answer, and
nobody is watching the rate.
