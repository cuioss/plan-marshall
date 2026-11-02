envelope_version=1
sender_type=plan
sender_id=plan-v02-46-upstream-close-after-early-answer
epic=lessons-routing
kind=finding
created=2026-10-22T18:04:15Z

# Recurrence: pre-push gate resolves zero bundles for a Maven reactor and records module-tests DEGRADED (plan-marshall:phase-6-finalize pre-push-quality-gate)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-46-upstream-close-after-early-answer (PR cuioss/API-Sheriff#513, merge e70743f), lessons-capture step.

Recurrence of api-sheriff-api-sheriff-0-2-0-005, -022 and -037 (and archived pm-mcp-core-m2-m4-104/-205/-216/-229/-250).

## Observation

`derive_gate_bundles` is shaped for marketplace bundles: every Java path of this Maven project landed in `unresolved` (0 bundles). `module-tests` has no canonical at default scope, so the pre-push gate recorded module-tests DEGRADED, although surefire ran inside `verify -Ppre-commit`.

## Why it matters

Still happening on every Maven plan in this epic. A gate arm that is always DEGRADED stops carrying information, and the real case (tests not run) cannot be told apart from it.

## Suggested direction

Unchanged from the earlier messages: resolve gate scope through the architecture module map for non-marketplace projects, and treat a quality-gate canonical that runs surefire as covering module-tests (or resolve a root-scope module-tests canonical for Maven).
