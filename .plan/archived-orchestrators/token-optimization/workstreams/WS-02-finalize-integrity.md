# WS-02: Finalize Integrity

epic: token-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-NN-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Close the phase-6-finalize correctness gaps that repeatedly cost bookkeeping and review rounds: commit/push integrity (loop-back push-strands, done-but-uncommitted leaves, lessons-capture tree-dirtying, worktree-remove-before-integrate), unified per-push finding triage, and the docs-contract drift around the `*_without_asking` family. Closes when P1, P2, and P7 have shipped.

## Scope

- In scope: phase-6-finalize steps and workflow docs, workflow-integration-git finalize surface, finalize triage flow, finalize-related concept/config docs.
- Out of scope: merge-queue mechanics (WS-04 / PLAN-08), metrics attribution (WS-04 / PLAN-09).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-p1-finalize-commit-integrity | launched | Commit/push integrity cluster incl. worktree-remove precondition |
| PLAN-02-p2-unified-finalize-triage | staged | One triage over the union of producer findings; after PLAN-01 |
| PLAN-07-p7-docs-contract-consistency | staged | `*_without_asking` family + HALT-vs-doc consistency; after PLAN-01/02 |

## Sequencing and Surface Notes

- PLAN-01 → PLAN-02 serialize (shared phase-6 files); fold into one plan is an accepted alternative.
- PLAN-07 sequences after both; docs-only, then disjoint from everything else.
