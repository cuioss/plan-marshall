# PLAN-08: Process contracts for the plan lane

epic: process-compliance
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-08-process-contracts.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.
>
> Provenance: transferred from `quality-aspect` (2026-09-19 full-corpus ingestion) at
> operator direction — documented-lane vs built-lane gaps are compliant-path coverage,
> owned by WS-03. Lesson evidence lives at
> `.plan/local/orchestrator/quality-aspect/lessons-archive/{id}.md`.

## Objective

Close the eight process-contract gaps so the documented lane matches the built lane:
no direct gh/glab bypasses, PR bodies editable through the abstraction, intent
rendered once, re-review budgets honored by leaves,
manifest snapshots plan-local, findings persisted, counts re-derived, footprint
pruned when non-empty.

## Deliverables

1. decision.log visibility for self-reported bypasses (lesson 2026-09-03-02-001).
2. PR-body edit flow without gh bypass (lesson 2026-09-03-02-002).
3. Intent-section idempotent rendering (lesson 2026-09-03-02-003).
4. Re-review timeouts dispatchable within leaf budgets (lesson 2026-09-03-02-004).
5. Plan-local manifest snapshots over global marshal.json (lesson 2026-09-03-02-006).
6. Self-review findings persisted to the finding store (lesson 2026-09-03-02-007).
7. Outline counts re-derived, include_unrealised fixed (lesson 2026-09-03-02-008).
8. Footprint prune gated on non-empty footprint (lesson 2026-09-03-02-009).

(Folded drain 2026-09-21, `phase-gates-009.md`: barrier-ask-override precedent for a
spend-capped stale review bot — incapacitated required reviewer + all other signals
green → escalate to operator, persist the override as a HEAD-bound gap-class
merge-authorization record, never an undocumented skip. Precedent note for the
merge-authorization flows this spec already covers; expected surface unchanged by this
fold — adds no file surface, recorded explicitly.)

(8 deliverables. The pytest-basetemp lesson is single-owned by test-quality
PLAN-180 — no duplication; see quality-aspect lessons-disposition.md § Transfers out.)

## Claim Labels

- OBSERVED: nine process lessons listable but unaddressable (YAML headers), each naming a doc-vs-behavior gap — read at `.plan/local/orchestrator/quality-aspect/lessons-archive/2026-09-03-02-001.md` et seq. (title triage; bodies verified at outline).
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: quality-aspect lessons-archive titles cited; bodies not opened this pass
- HYPOTHESIS: one contract pass over the plan lane closes all nine without cross-plan refactors — confirm/refute at `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` § CI abstraction read surface (verify-at-outline).
  - verdict: corroborated | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: tools-integration-ci ci.py and ci_base.py present

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` — CI abstraction.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/` — intent rendering, PR bodies.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none in this epic (CI/github contract surfaces touch no staged WS-01–WS-06 surface).
- Adjacent to: quality-aspect PLAN-18 merge-queue proof reads the same CI surface without touching it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-08-process-contracts.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
