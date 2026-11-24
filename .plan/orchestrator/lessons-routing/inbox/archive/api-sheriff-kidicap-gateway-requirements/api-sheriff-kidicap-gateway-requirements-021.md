envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:28Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: the merge-lock release reported the lock "already free" although the plan had acquired it

Observation (ledger, operator report in PLAN-17's landing): during PLAN-17's finalize the release reported the lock "already free" although that plan had acquired it. The merge was unaffected, but the release path did not observe its own claim, so mutual exclusion is unestablished for that window and the report reads as success. Filed earlier as plan-marshall lesson `2026-09-23-05-003`; routed here with the evidence.

Component hint: `plan-marshall:manage-locks` merge mutex release.
