# PLAN-050: Plan State and Records Test Reduction

epic: test-quality
workstream: WS-02

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-050.md`](../landings/PLAN-050.md),
> and the full original brief plus every run report is under
> [`archive/050-plan-state-and-records-test-reduction/`](../archive/050-plan-state-and-records-test-reduction/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Apply the house style to the plan-state and records slice. This slice carried the epic's two largest
modules — `test_audit_checks.py` at ~8,700 lines over ~90 classes and `test_audit.py` at ~1,500 — and
decomposing them into check-named modules reachable by filename is the epic's worked example of what the
**B1** split looks like when it lands. Two runs.

## Deliverables

1. D1 — decompose `test_audit_checks.py` into per-check modules with shared builders in
   `_audit_fixtures.py`; every check in the skill's inventory reachable by filename.
2. D2 — retire the per-subcommand `argparse.Namespace` builders via `parse_ns` (**B6**).
3. D3 — hoist fixture builders into one `_{domain}_fixtures.py` per directory (**B4** + **B10**).
4. D4 — split every module over the 400-line budget.
5. D5 — parametrize the tabular families (**B5**) and strip historical prose (**B3**).
6. D6 — report the measured deltas, each with the command that produced it.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside PLAN-080's recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: `test/plan-marshall/audit-archived-plan-retrospectives/`
- OBSERVED: `test/plan-marshall/manage-adr/`, `test/plan-marshall/manage-change-ledger/`
- OBSERVED: `test/plan-marshall/manage-findings/`, `test/plan-marshall/manage-lessons/`
- OBSERVED: `test/plan-marshall/manage-locks/`, `test/plan-marshall/manage-metrics/`
- OBSERVED: `test/plan-marshall/manage-status/`, `test/plan-marshall/manage-tasks/`
- OBSERVED: `test/plan-marshall/plan-retrospective/`
- OBSERVED: `test/plan-marshall/test_lessons_capture_workflow.py`, `test_lessons_consult_workflow.py`,
  `test_recipe_lesson_cleanup.py`

## Dependencies and Sequencing

- Depends on: PLAN-010 and PLAN-020 (landed).
- Overlaps with: PLAN-140 run 1's successor work and PLAN-105 § D5, both of which edit this slice.
- Adjacent to: `test/conftest.py` and `test/_shared/**`, consumed read-only.

## Hand-Off Command

Not emittable — this plan has landed.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
