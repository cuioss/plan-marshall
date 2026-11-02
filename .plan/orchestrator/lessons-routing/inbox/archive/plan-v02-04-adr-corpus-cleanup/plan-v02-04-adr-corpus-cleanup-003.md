envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=finding
created=2026-10-26T09:55:51Z

# Recurrence: pre-push-quality-gate cannot run module tests at root scope in a Maven reactor, so it always reports DEGRADED (plan-marshall:phase-6-finalize pre-push-quality-gate)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

Recurrence of `lessons-routing-031` ("Gate-bundle derivation zero on Maven; pre-push gate DEGRADED") and the earlier cluster 008, 037, 043, 044, 068, 104, 119 in the lessons-archive INDEX.

## Observation

The step recorded `0 bundles + whole-tree gates green, module-tests DEGRADED` on all three firings of this plan. In this repository the gate cannot run module tests at root scope, so the module-tests arm degrades on every run regardless of the footprint. The verdict carries no information about the change.

## Why it matters

A gate arm that is DEGRADED on every run is ignored by operators and reviewers, which hides the run where the degradation would matter.

## Suggested direction

Resolve the Maven reactor's module-tests canonical per module (or the root `test` goal through the build executor) instead of degrading; or record the arm as "not applicable for this build system" with an explicit reason, so DEGRADED stays reserved for real failures.
