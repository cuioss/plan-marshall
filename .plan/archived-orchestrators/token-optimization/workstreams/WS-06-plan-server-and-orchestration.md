# WS-06: Plan-Server and Orchestration

epic: token-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The capability track above the plan lifecycle: the marshall-orchestrator skill itself (whose D10 dogfood created this epic), the plan-server ladder (Rung 1 global-home root → Rung 2 marshalld build server; BK #912, the keystone, SHIPPED), the parked ci-pr-safe-merge plan, and the deferred consumer upgrade migrations. Closes when the orchestration/plan-server capabilities are shipped and the consumers are migrated.

## Scope

- In scope: marshall-orchestrator skill tree, `marketplace_paths.py` resolver surface (D0 + Rung 1), plan-server design/implementation, ci-pr-safe-merge, consumer-repo upgrade runs.
- Out of scope: everything repo-local owned by WS-02..WS-05.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-12-marshall-orchestrator-skill | launched | Running as plan-marshall plan `marshall-orchestrator` |
| PLAN-13-rung1-global-home-root | parked | Sequenced BEHIND PLAN-12's D0 (same `marketplace_paths.py` resolver); restart contract in `plans/plan-global-home-root.md` |
| PLAN-14-ci-pr-safe-merge | parked | Resume at 3-outline: `/plan-marshall plan=ci-pr-safe-merge` |
| PLAN-15-consumer-upgrade-migrations | parked | Deferred by operator 2026-07-16; API-Sheriff first (sharpest #908 acceptance), nifi LAST |

## Sequencing and Surface Notes

- PLAN-12 → PLAN-13 is a HARD sequence: both rewrite the `marketplace_paths.py` resolver; D0 is the general mechanism, Rung 1 extends it with a home-anchored variant (do NOT assume coverage).
- Rung 2 (plan-server-core) is design-READY but gated behind Rung 1; not yet a queue entry.
- PLAN-15 runs in consumer repos — surface-disjoint from every repo-local plan by construction.
