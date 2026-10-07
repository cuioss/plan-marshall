# PLAN-100: Module-Budget Campaign (Run 1 of 7)

epic: test-quality
workstream: WS-04

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the queue
> reconciles both ways; the **authoritative verdict** is [`landings/PLAN-100.md`](../landings/PLAN-100.md),
> and the full original brief plus every run report is under
> [`archive/100-module-budget-campaign/`](../archive/100-module-budget-campaign/).
> Nothing here is re-emittable — a re-entry against this slice is staged as its own new spec.

## Objective

Drive **B1**, the 400-line module budget, to zero — the epic's one structural rule and the one nobody
reached, because every reduction plan sequenced its split deliverable last and every run exhausted its
budget first. This is a campaign of seven runs, one slice each, measured against the budget rather than
against a line target. ⛔ **Run 1 landed; runs 2–7 are re-staged as PLAN-140.**

## Deliverables

1. D1 — re-derive the whole-tree count and the per-slice attribution before acting.
2. D2 — split the run's slice by behaviour cluster; ⛔ **never split a class**.
3. D3 — fidelity: the `Class::test` multiset and the comment/code-line counts identical across the move.
4. D4 — reduce duplication across the slice's directories.
5. D5 — report the measured deltas, each with the command that produced it.

## Claim Labels

Every claim this spec carried was settled by the ingestion ground-truth check at HEAD `2cd1a19c`; the
per-deliverable verdicts are in the landing record rather than restated here, because a landed plan's
claims are settled facts and the landing record is their single home.

- OBSERVED: the slice's directory list is disjoint from every other reduction slice's — read at the epic's
  partition, re-verified during ingestion (the whole-tree budget attribution sums exactly, with no residual)
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca; verdict UNCHANGED but the reasoning is CORRECTED. The claim that the whole-tree budget attribution sums exactly WITH NO RESIDUAL is false: the population is 279 (was 267 when written, then 270), confirmed by three independent methods that agree exactly - doctor rules_run, an independent git ls-tree plus wc -l sweep, and PLAN-120's landed attribution derivation. CORRECTION: the previous stamp of this verdict blamed test/pm-plugin-development/cloud-plan-lane/ being claimed by no spec. PLAN-120's derivation REFUTES that - unclaimed is 0 whole-tree and that directory falls inside PLAN-080's recursive test/pm-plugin-development/** glob. The residual is population growth from other epics' landings, not an ownership hole. rescoped: no - a LANDED spec is history and is never re-scoped; the live successor is PLAN-170

## Expected Surface

- OBSERVED: one reduction slice per run, `test_*.py` only — run 1 took PLAN-050's ten directories under
  `test/plan-marshall/` plus its three root modules
- OBSERVED: the remaining six rows are enumerated in
  [`PLAN-140`](PLAN-140-module-budget-campaign-runs-2-7.md), which supersedes this spec's forward half
- OBSERVED: **no helper module.** The budget rule cannot see them, which is PLAN-105 § D3's subject

## Dependencies and Sequencing

- Depends on: PLAN-010 and PLAN-020, and on each slice's own plan having landed before the campaign takes
  that slice. All six have.
- Overlaps with: every reduction slice as the campaign reaches it, and PLAN-105, which closes run 1's
  leftovers and must land before run 2.
- Adjacent to: `test/conftest.py` and `test/_shared/**`, never edited.

## Hand-Off Command

Not emittable — this plan has landed.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
