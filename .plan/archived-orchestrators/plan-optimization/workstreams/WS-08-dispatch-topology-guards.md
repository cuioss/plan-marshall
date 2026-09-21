# WS-08: Dispatch-Topology Guards

epic: plan-optimization

> Charter document for one workstream. Tracked in the epic `status.json` `workstreams[]` field.

## Charter

Add a proactive guard against a planning-phase / dispatched-leaf agent editing the MAIN checkout — a
correctness violation that recurred this epic (lesson 17-001 #920, then `2026-07-18-13-002` PLAN-05).
Both were caught-and-reverted, but only reactively. Closes when a planning-phase source mutation of
the main checkout is blocked (or loudly flagged) before it lands, not reverted after.

## Scope

- In scope: the phase-3-outline / phase-4-plan no-source-mutation invariant + a Q-Gate/topology guard
  that enforces it; `execution-context` main-vs-worktree checkout boundary.
- Out of scope: the leaf-validator sub-dispatch topology (PLAN-03, shipped); the build-gating
  footprint work (PLAN-11).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-16-planning-phase-checkout-guard | staged | Block/flag a planning-phase agent editing the MAIN checkout (lessons 17-001, 13-002) |

## Sequencing and Surface Notes

- Adjacent to in-flight PLAN-11 (both touch phase-4) — coordinate/rebase if they overlap. Disjoint
  from PLAN-10/12 and the other new plans.
