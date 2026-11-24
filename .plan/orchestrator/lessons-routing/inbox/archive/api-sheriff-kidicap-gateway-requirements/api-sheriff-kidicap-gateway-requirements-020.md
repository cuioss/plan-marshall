envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:27Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: `post_responses` transmitted internal triage prose verbatim as a public PR reply

Observation (ledger, PLAN-18 / #346; inbox `route-header-matcher-defects-003.md`): a PR-level comment `IC_kwDOPatrT88AAAABWb_adQ` on API-Sheriff #346 carries internal triage prose that `post_responses` sent unchanged as a public reply. Harmless there (the comment is to be deleted by hand), but the mechanism lets internal triage text reach a public thread. Filed earlier as plan-marshall lesson `2026-09-24-05-001`; routed here with the evidence.

Component hint: `plan-marshall:workflow-integration-github` `post_responses`.
