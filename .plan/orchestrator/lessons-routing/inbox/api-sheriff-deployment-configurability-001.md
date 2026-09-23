envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=lessons-routing
kind=finding
created=2026-09-23T07:24:29Z

# Forward from `deployment-configurability` (API-Sheriff) — `scope_creep_check` emits a finding type `manage-findings` rejects outright, so the guard can never persist

Surfaced during `plan-28-closeout-residual-hardening`'s phase-5-execute (three firings: 13:06:35,
14:51:29, 17:48:47). Reported to plan-marshall via `SendFeedback` in-run; also filed here for
durable cross-repo tracking, per the same convention this epic uses for every other plan-marshall
tooling gap it surfaces.

## What happened

`scope_creep_check` attempts to persist its verdict as a finding of type `scope_creep_warning`.
`manage-findings` rejects it outright:

> Invalid finding type: scope_creep_warning. Must be one of ('bug', 'improvement', 'anti-pattern',
> 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue',
> 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow')

The guard measured scope creep correctly on all three firings — residual counts of 9, 11 and 28
against a threshold of 5 — and could not file any of them. Each time, the measurement survived only
as inline prose in a `[VERIFY]` WARNING the executing agent chose to write. This is a
producer/consumer contract break between two scripts in the same bundle: the guard runs, gets the
right answer, and the answer never reaches the store any downstream reader consults. A reader
querying `manage-findings` for scope-creep evidence on this plan finds nothing — not "no creep", but
*nothing*, indistinguishable from a guard that never ran.

It recurred three times within a single plan because nothing about the failure is progressive: each
firing hits the identical rejection.

## Suggested remedy

A script that persists through another script's typed enum must draw its type from that enum. Where
a genuinely new finding type is needed (`scope_creep_warning`), adding it to `manage-findings`'s
accepted type set is part of the same change as emitting it. A guard whose persist path can fail
should treat persist failure as a loud outcome, not a warning it hopes someone reads.

## Confirmed as non-scope-creep

In all three firings the executing agent confirmed the residual paths were the plan's own
already-committed loop-back footprint rather than genuine scope creep, so no actual scope-creep
incident was missed by this failure — but the store gap means a future incident could be.

## Source

`deployment-configurability` epic (API-Sheriff), PLAN-28 (`plan-28-closeout-residual-hardening`, PR
#341, merged `1994f28`). Original candidate-lesson message:
`plan-28-closeout-residual-hardening-012.md` (discarded from that epic's own lessons corpus as
out-of-scope plan-marshall tooling, routed here instead).
