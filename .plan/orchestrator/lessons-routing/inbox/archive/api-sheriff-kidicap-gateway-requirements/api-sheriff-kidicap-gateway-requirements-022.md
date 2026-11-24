envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:29Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: a landing's `review_body_findings_total` disagrees with the provider

Observation (ledger, PLAN-31 landing, 2026-11-15, re-read then): the landing claimed 5; `review-gate` on the merged head read 4 (and 0 dispositions, which only the run's progress file can settle). The thread count (0) matched. Recorded in API Sheriff's landing record as a false claim.

Related, from the PLAN-33 landing (2026-11-24, see the PLAN-33 message in this series): there the same key is `unknown` because no step parsed the review bodies. Two different failure modes of one fact.

Component hint: the `landing-facts` producer (review-body count) and `runbook_lane review-gate`.
