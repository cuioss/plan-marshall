# WS-02: Worktree discipline

epic: process-compliance

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the worktree-materialization and main-clean invariants: a persisted
`worktree_materialized` flag, refusal of phase-5 dispatch while unset, per-boundary
main-clean assertions, and a hand-off admission gate before the first edit. Closes
when work on main with an unmaterialized worktree is structurally refused.

## Scope

- In scope: `prepare_execute` flag, phase-5 dispatch guards, phase-boundary main-clean assertions, hand-off/session-start tree checks
- Out of scope: phase artifact gates (WS-01), generator/wrapper contracts (WS-03), opencode runtime (WS-06)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-02-worktree-discipline | staged | Materialization flag, boundary checks, hand-off gate |

## Sequencing and Surface Notes

- PLAN-02 sits adjacent to WS-01 (both touch phase boundaries) without overlapping files: WS-01 owns `manage-status`, WS-02 owns `prepare_execute`/phase-5 dispatch readers.
