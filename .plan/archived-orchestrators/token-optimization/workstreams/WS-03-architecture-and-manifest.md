# WS-03: Architecture and Manifest

epic: token-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Fix the architecture-resolution and execution-manifest gap clusters: build_map classification, skills_by_profile resolution, mutating verify-profile, execution_tier routing coverage, and the `enhancement` change_type drop. Closes when P3 and P4 have shipped.

## Scope

- In scope: manage-architecture (resolve/classify surfaces), manage-execution-manifest (compose/routing).
- Out of scope: build-tool extension glob tables (shipped #909), finalize steps (WS-02).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-p3-architecture-resolution | launched | build_map classify + skills_by_profile + mutating verify-profile |
| PLAN-04-p4-execution-manifest-gaps | launched | execution_tier routing + change_type drop + TS #576 "Gap C" (aspect-classify tokenizer) |

## Sequencing and Surface Notes

- PLAN-03 ∥ PLAN-04 are surface-disjoint (per the source ledger's parallel set) and disjoint from WS-02/WS-04/WS-05 launches.
