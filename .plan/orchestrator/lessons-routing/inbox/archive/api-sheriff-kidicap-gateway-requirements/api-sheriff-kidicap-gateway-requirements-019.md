envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:27Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: `source_id` is a stored PATH, so a ledger relocation orphans every in-flight plan's outbox

Observation (ledger, PLAN-23 landing, reproduced both ways 2026-10-02): PLAN-23 shipped #369 with `emit-landing` reporting "not orchestrated, no landing emitted". Its `source_id` was persisted on 2026-09-25 as `.plan/local/orchestrator/.../PLAN-23-....md`; the executor regeneration to 0.1.1826 (2026-10-01) made that the RETIRED address, giving `detection: unrecognised_id`, `orchestrated: false`. The regeneration alone was sufficient; the later ledger move made the new address correct without rewriting the pointer the running plan already held. The landing was recovered from an operator paste, so nothing was lost, but the automatic channel was broken mid-flight, which none of four earlier detector-disagreement recurrences had yet produced.

Mitigation in use until the pointer is resolved dynamically: do not relocate the ledger while a plan is in flight. Filed earlier as a plan-marshall lesson; routed here with the evidence.

Component hint: `plan-marshall:plan-orchestrator` (`inbox detect`, `emit-landing`), `source_id` resolution at finalize time.
