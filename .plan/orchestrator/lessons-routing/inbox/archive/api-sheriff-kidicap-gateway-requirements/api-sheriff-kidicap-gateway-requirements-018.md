envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:19Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: `ci-verify` files this repository's Maven build jobs as `ci_policy_failure`

Observation (ledger, plans PLAN-13 and PLAN-16; inbox `plan-13-defect-fixes-002.md`, `plan-16-application-portal-004.md`): the job names `build / build (25|26)`, `build / sonar-build`, `build / conclusion` and `integration-tests / test` contain none of the build-profile tokens the producer matches (`verify`, `quality-gate`, `module-tests`, `coverage`), so every red build or test job is routed to the policy triage producer instead of the build-failure one.

Recurrence: in PLAN-16 (2026-09-22) a plain unit-test failure in `build (25)` was presented as a CI policy failure, and the later green `ci_verify` did not overwrite the loop-back record (corrected by hand in that run).

Remedy named in the ledger: project configuration (the architecture match rule / `marshall-steward`), not API Sheriff product work. Already promoted as plan-marshall lesson `2026-09-22-18-004`; routed here so the owning repository sees it with its evidence.

Component hint: `plan-marshall:phase-6-finalize` ci-verify, architecture match rule.
