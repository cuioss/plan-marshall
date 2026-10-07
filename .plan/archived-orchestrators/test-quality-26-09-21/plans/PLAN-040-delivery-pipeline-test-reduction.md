# PLAN-040: Delivery Pipeline Test Reduction

epic: test-quality
workstream: WS-02

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-040.md`](../landings/PLAN-040.md),
> and the full original brief plus every run report is under
> [`archive/040-delivery-pipeline-test-reduction/`](../archive/040-delivery-pipeline-test-reduction/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Apply the house style to the delivery-pipeline slice — the finalize phase, the CI and Git provider
integrations, and the review apparatus. The slice's distinguishing feature is a large subprocess test layer
asserting contracts an in-process test already covers, which **B9** says should collapse to a per-script
CLI-plumbing smoke.

## Deliverables

1. D1 — strip history from docstrings and comments (**B3**).
2. D2 — one fixture corpus and one driver per module (**B4**).
3. D3 — collapse the duplicated subprocess/in-process assertion layer (**B9**), naming each collapse beside
   the in-process test that subsumes it.
4. D4 — split every module over the 400-line budget.
5. D5 — normalise preambles (**B7**) and namespaces (**B6**), listing every conversion exception.
6. D6 — report the measured deltas, each with the command that produced it.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside PLAN-080's recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: `test/plan-marshall/automatic-review/`, `test/plan-marshall/manage-ci-artifacts/`
- OBSERVED: `test/plan-marshall/phase-5-execute/`, `test/plan-marshall/phase-6-finalize/`
- OBSERVED: `test/plan-marshall/tools-integration-ci/`, `test/plan-marshall/workflow-shared/`
- OBSERVED: `test/plan-marshall/workflow-integration-git/`, `.../workflow-integration-github/`,
  `.../workflow-integration-gitlab/`, `.../workflow-integration-sonar/`
- OBSERVED: `test/plan-marshall/workflow-permission-web/`, `test/plan-marshall/workflow-pr-doctor/`
- OBSERVED: `test/plan-marshall/test_phase_6_finalize_step_id_consistency.py`,
  `test_triage_loop_back_target.py`, `test_workflow_integration_github_ci_aggregation.py`,
  `test_workflow_integration_gitlab_ci_aggregation.py`, `_ci_wait_contract.py`

## Dependencies and Sequencing

- Depends on: PLAN-010 and PLAN-020 (landed).
- Overlaps with: PLAN-110, which writes skip sites in `phase-6-finalize/`, `workflow-integration-git/` and
  `workflow-integration-github/`.
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
