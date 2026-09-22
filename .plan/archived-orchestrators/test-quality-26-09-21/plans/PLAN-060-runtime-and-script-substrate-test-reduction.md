# PLAN-060: Runtime and Script Substrate Test Reduction

epic: test-quality
workstream: WS-02

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-060.md`](../landings/PLAN-060.md),
> and the full original brief plus every run report is under
> [`archive/060-runtime-and-script-substrate-test-reduction/`](../archive/060-runtime-and-script-substrate-test-reduction/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Apply the house style to the runtime and script-substrate slice — the loader, the platform runtime, the
file and permission tooling, and the shared script infrastructure. The slice's distinguishing feature is a
very high ratio of inline `monkeypatch` isolation to declared fixtures, and a large set of near-identical
test skeletons that includes deliberate matched control pairs. Three runs.

## Deliverables

1. D1 — hoist repeated `monkeypatch` isolation into function-scoped, explicitly-requested fixtures (**B4**).
2. D2 — split every module over the 400-line budget.
3. D3 — **B6** `parse_ns` everywhere reachable; **B7** no `spec_from_file_location`.
4. D4 — **B5** parametrize the tabular families; **B3** strip historical prose.
5. D5 — derive the property-based-testing candidate list; add no dependency.
6. D6 — report the measured deltas, each with the command that produced it.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside PLAN-080's recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: `test/plan-marshall/extension-api/`, `test/plan-marshall/lsp-client/`
- OBSERVED: `test/plan-marshall/manage-files/`, `test/plan-marshall/manage-logging/`
- OBSERVED: `test/plan-marshall/manage-providers/`, `test/plan-marshall/platform-runtime/`
- OBSERVED: `test/plan-marshall/ref-toon-format/`, `test/plan-marshall/script-shared/`
- OBSERVED: `test/plan-marshall/tools-file-ops/`, `test/plan-marshall/tools-input-validation/`
- OBSERVED: `test/plan-marshall/tools-permission-doctor/`, `test/plan-marshall/tools-permission-fix/`
- OBSERVED: `test/plan-marshall/tools-script-executor/`, `test/plan-marshall/untrusted-ingestion/`

## Dependencies and Sequencing

- Depends on: PLAN-010 and PLAN-020 (landed).
- Overlaps with: PLAN-155, which closes this slice's parametrization half; PLAN-110, whose skip sites and
  in-process stub sit in `lsp-client/`, `platform-runtime/` and `tools-file-ops/`.
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
