# WS-06: Phase Lifecycle & Planning Mechanics

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-06-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns the plan-lifecycle machinery from tasks-file staging through phase-5 absorb to
gate predicates: no stale file silently read, no upstream commit absorbed as no-overlap,
no worktree-resolved plan reported missing. Closed
when every lifecycle transition resolves its paths in the tree the plan actually runs in.

## Scope

- In scope: phase-4-plan staging and guards, phase-5-execute absorb/chain/outcome,
  manage-tasks freshness, phase_handshake diagnostics, refine heuristics,
  B7/triage predicates, worktree path resolution, STATUS barrier.
- Out of scope: outline declarations (WS-05), finalize self-review (WS-08).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-10-plan-execute-mechanics | staged | Tasks staging, freshness, absorb, chain-tail, scope changes |
| PLAN-11-gate-predicates | staged | Refine heuristics, B7 carve-out, handshake, STATUS barrier |
| PLAN-12-worktree-paths | staged | CWD-pinned resolution, localized parsing, argparse rejections |

## Sequencing and Surface Notes

- PLAN-10, PLAN-11, PLAN-12 touch adjacent lifecycle surfaces; PLAN-10 first
  (task/phase-5 primitives), then PLAN-11 and PLAN-12 (disjoint skills:
  refine/plan-marshall/status vs lessons/architecture) may pair.
