# PLAN-070: Architecture and Orchestration Test Reduction

epic: test-quality
workstream: WS-02

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-070.md`](../landings/PLAN-070.md),
> and the full original brief plus every run report is under
> [`archive/070-architecture-and-orchestration-test-reduction/`](../archive/070-architecture-and-orchestration-test-reduction/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Apply the house style to the architecture and orchestration slice — the build extensions, the plan
lifecycle phases, the orchestrator, and the finalize steps. The slice carries the epic's largest population
of hand-built argument namespaces against near-zero adoption of the shared `parse_ns` helper.

## Deliverables

1. D1 — rename the two `*_test_helpers.py` modules per **B10** and consolidate the six `build-*`
   directories onto the shared fixture.
2. D2 — build one plan-lifecycle staging fixture on `plan_context`, **only if** the nine phase and
   lifecycle directories do not already share staging; otherwise say so rather than building a second.
3. D3 — **B7** eliminate `spec_from_file_location` and deep parent chains; **B6** convert namespaces to
   `parse_ns`.
4. D4 — **B3** strip historical-prose citations; **B5** parametrize the tabular families.
5. D5 — report the measured deltas, each with the command that produced it.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside PLAN-080's recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: `test/plan-marshall/build-gradle/`, `build-maven/`, `build-npm/`, `build-operations/`,
  `build-pyproject/`, `build-server/`
- OBSERVED: `test/plan-marshall/execute-task/`, `manage-architecture/`, `manage-lifecycle/`,
  `manage-personas/`, `manage-plan-documents/`, `manage-terminal-title/`
- OBSERVED: `test/plan-marshall/phase-1-init/`, `phase-2-refine/`, `phase-3-outline/`, `phase-4-plan/`
- OBSERVED: `test/plan-marshall/plan-doctor/`, `plan-marshall/`, `plan-orchestrator/`
- OBSERVED: `test/plan-marshall/finalize-step-plugin-doctor/`, `finalize-step-preference-emitter/`,
  `finalize-step-review-retrospective/`, `finalize-step-sync-baseline/`, `finalize-step-sync-plugin-cache/`
- OBSERVED: `test/plan-marshall/q-gate-validation-agent/`, `ref-workflow-architecture/`, `targets-claude/`
- OBSERVED: `test/plan-marshall/test_lane_refactor_cleanup_sweep.py`,
  `test_plan_marshall_plugin_extension.py`

## Dependencies and Sequencing

- Depends on: PLAN-010 and PLAN-020 (landed).
- Overlaps with: PLAN-150, which closes this slice's **B6** conversion; PLAN-140 run 5, which splits it;
  PLAN-135, whose three contradiction sites are in `build-gradle/`, `build-npm/` and `build-operations/`;
  PLAN-110, which records a platform exception in `build-server/`.
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
