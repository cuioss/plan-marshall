# PLAN-080: Plugin Development and Generator Test Reduction

epic: test-quality
workstream: WS-02

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-080.md`](../landings/PLAN-080.md),
> and the full original brief plus every run report is under
> [`archive/080-plugin-development-and-generator-test-reduction/`](../archive/080-plugin-development-and-generator-test-reduction/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Apply the house style to the plugin-development and generator slice — the doctor analyzers, the
marketplace generator and its targets, the cache sync, and every `pm-*` bundle test directory. The slice's
distinguishing feature is a large family of `test_analyze_*.py` modules that each hand-run an analyzer,
where a shared assertion scaffold already exists. Two runs.

## Deliverables

1. D1 — rename `_fixtures.py` per **B10** and convert the `test_analyze_*.py` modules onto the shared
   `assert_analyzer_findings` scaffold.
2. D2 — preserve the suite-coverage meta-test through every D1 move; `EXEMPT_RULE_IDS` must not grow.
3. D3 — **B7** eliminate `spec_from_file_location`; **B6** convert namespaces to `parse_ns`.
4. D4 — derive the property-based-testing candidate list for the generator half.
5. D5 — report the measured deltas, each with the command that produced it.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside THIS spec's own recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: `test/pm-plugin-development/**` — ⛔ **excluding
  `plugin-doctor/test_test_conventions_rule*.py`**, which is PLAN-010's permanently carved-out glob
- OBSERVED: `test/marketplace/**`, `test/sync-plugin-cache/`
- OBSERVED: `test/finalize-step-deploy-target/`, `test/finalize-step-sync-plugin-cache/`
- OBSERVED: `test/pm-dev-frontend/`, `test/pm-dev-frontend-cui/`, `test/pm-dev-java/`,
  `test/pm-dev-java-cui/`, `test/pm-dev-oci/`, `test/pm-dev-python/`, `test/pm-documents/`
- OBSERVED: `test/default/`, `test/pm-code-intelligence/`
- OBSERVED: `test/test_runner_falsifiability.py`, `test/test_conftest_discipline.py`

## Dependencies and Sequencing

- Depends on: PLAN-010, PLAN-020 and PLAN-090 (all landed).
- Overlaps with: PLAN-140 run 6, which splits this slice; PLAN-110, whose largest concentrations of skip
  sites are in `test/sync-plugin-cache/`, `test/pm-plugin-development/` and `test/marketplace/`.
- Adjacent to: PLAN-010's rule-test glob, excluded outright — the stronger guarantee for a plan that never
  edits those modules at all.

## Hand-Off Command

Not emittable — this plan has landed.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
