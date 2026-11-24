envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:30Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: PLAN-33's landing facts: unknowns, an unconsulted merge stamp and an unchecked freshness coverage

Observation (inbox landing `plan-33-adapt-to-token-sheriff-0-9-9-001.md`, merged as API-Sheriff #656; `inbox landing-check` returned `complete: false`, `missing_keys` = `effort`, `review_body_findings_total`, `review_body_findings_handled`; the first two re-read in this run via `landing-check`, the rest from the landing's own residue):

1. `effort=unknown`: the plan carries no effort stamp, although the dispatched steps ran under execution-context levels 5 and 6.
2. `review_body_findings_total` and `review_body_findings_handled` are `unknown`: the manifest had no `review-gate` step and no step parsed the review bodies. Re-read in this run: `ci pr comments --pr-number 656 --unresolved-only` reports 9 unresolved rows (6 `issue_comment`, 3 `review_body`), every one with an EMPTY thread id, so `unresolved_review_threads=0` is right but the nine rows can never be resolved and are reported unresolved forever.
3. The merge passed with `finalize-step-sync-baseline` listed by the merge gate as an unconsulted stamp (the step declares no head dependence).
4. The pre-push freshness gate answered `fresh` with `scope_cross_check: undetermined` (`required_coverage_unknown`): a whole-tree build row matched the tree but its coverage of the change was not checked.
5. The preference-emitter's one over-threshold recurrence carried module `maven` (the build tool's attribution tag, not one of the ten architecture modules), so no owed `architecture enrich` call was filed.
6. Cost figures from the landing: `total_tokens=81692289`, `total_wall_seconds=158809.0` (about 44 h); the code review and functional review each spent 3 of 5 loop-back rounds.

Component hint: `plan-marshall:phase-6-finalize` (emit-landing, merge gate, freshness gate, preference-emitter).
