envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:32Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: `handle-open` presents one item per turn, which for 50 items is 50 turns, and its threshold does not persist as the operator expects

Observation (2026-11-23/24, epic with 52 open items, 14 of them standing practice notes):
1. The contract caps confidence at the threshold for any claim not re-read this run, so almost nothing is decidable without a per-item re-read; with the one-per-turn presentation rule the operator asked for batching ("revisit all findings, decide if you are 60% confident") and the run had to improvise grouped presentation (practice notes, release/downstream watches, CI-run watches, outside-the-epic items, product gaps). A grouped mode with one answer per group would fit.
2. The threshold semantics are "strictly greater than"; an operator who says "decide if you are 60% confident" means at least 60, and a recommendation at exactly the threshold falls into the presented set.
3. The knob `orchestrator.decision_confidence_threshold` set to 75 early in the run (via `manage-config orchestrator set`) was found back at 90 later, with an unmodified `.plan/marshal.json`; the cause is not known (an operator revert is possible, not confirmed). The operator later also wanted the lowered value for that run only, which a per-run `threshold=N` argument covers; it was not used because the request arrived as free text.
4. A related read: `orchestrator corpus verdicts` returned 427 KB (138 stale rows, each with its full list of matched paths) for a 22-spec corpus, which is hard to consume inline.

Component hint: `plan-marshall:plan-orchestrator` `workflow/handle-open.md`, `standards/orchestration-model.md` § Handle-Open Contract, `corpus verdicts` output shape.
