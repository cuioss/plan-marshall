envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-25T22:12:14Z

# Recurrence: pre-push-quality-gate resolves no bundles and no test canonicals for a Maven reactor (plan-marshall:phase-6-finalize pre-push-quality-gate, build-maven canonical resolution)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-27-test-simplification (PR cuioss/API-Sheriff#520), inbox message plan-v02-27-test-simplification-004.

Recurrence of lessons-routing messages api-sheriff-api-sheriff-0-2-0-022 and -037. `derive_gate_bundles` found 0 bundles for the multi-module reactor, and both `test-compile` and `module-tests` resolved to `architecture_error`. The step degraded every time to the whole-tree quality gate (`verify -Ppre-commit`), and said so honestly (plan decision-log entries 037fba, ab51a4 and e10673b8). The per-bundle and targeted-test layer never ran.

Suggested direction: as in -022 and -037, resolve the canonicals for build-maven modules from the architecture inventory (for example `test -pl api-sheriff -am`). When they cannot resolve, report one explicit "not applicable here" signal instead of an `architecture_error` per canonical, so the operator can tell non-fit from broken.
