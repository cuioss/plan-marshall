# WS-04: Tooling and Metrics

epic: token-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Retire the accumulated small-tooling and measurement debt: the misc tooling batch (ADR numbering, npm warn-gate, cross-repo lesson-store trap, CI mypy over `test/`, merge_lock notation), the merge-queue squash-strategy override, the metrics-attribution unsoundness that makes the token corpus lossy, and the stale `build-busy` title token. Closes when P6, P8, P9, and TT have shipped.

## Scope

- In scope: small cross-cutting tooling fixes, tools-integration-ci merge path, manage-metrics attribution, manage-status title_token lifecycle.
- Out of scope: finalize steps (WS-02), architecture/manifest surfaces (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-06-p6-small-tooling-batch | staged | Includes the manage-lessons store≠component-repo structural guard |
| PLAN-08-p8-merge-queue-squash-reconcile | launched | Queue merge-method silently overrides `pr_merge_strategy=squash` |
| PLAN-09-p9-metrics-corpus-integrity | staged | Inline=0 attribution, dispatched under-count, loop-back timestamp corruption |
| PLAN-11-tt-terminal-title-stale-build-busy | staged | Re-scope at outline — BK #912 state-gate-first wake may have dissolved the dangling case |

## Sequencing and Surface Notes

- PLAN-06 ∥ PLAN-08 ∥ PLAN-09 are in the source ledger's disjoint parallel set.
- PLAN-11 is independent but small; verify the premise still holds before launching.
