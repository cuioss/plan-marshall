# WS-03: Orchestrator Launch Gate

epic: live-blockers

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-orchestrator-launch.md` and is tracked in the
> `workstreams[]` field of the epic header, `status.json`. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The orchestrator's own emission gate, which this epic runs on. The workstream closes when `next` can emit a plan without an operator override while an unrelated spec or plan is indeterminate.

## Scope

- In scope: `corpus cross-check`, the admission rule in `orchestrate.md` Step 4
- Out of scope: the rest of the orchestrator scripts; smaller emission and readiness defects are in `backlog.md` § 3.3

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-LB-14-launch-gate-scope | staged | An indeterminate candidate blocks only what it could collide with |

## Sequencing and Surface Notes

- Run early: it unblocks this epic's own `next`.
