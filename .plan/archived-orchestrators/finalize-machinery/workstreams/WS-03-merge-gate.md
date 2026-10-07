# WS-03: Merge gate and branch mechanics

epic: finalize-machinery

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-merge-gate.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns the merge-gate correctness holes found on PR #1409 plus the git branch-mechanics
defects: the currency guard credits stale reviews, the issue-comment path misreads
current reviews as declined, the required-bot set interacts with the rate-window await,
and branch-sync-state / prune-ref fail exactly when cleanup has run. The outcome is a
gate that compares what the bot says it reviewed and branch verbs reachable in the
states cleanup produces.

## Scope

- In scope: workflow-integration-github currency and head_sha paths, automatic-review
  gate/registry/completeness scripts, marshal.json required-bot + await pairing,
  workflow-integration-git branch-sync-state and prune-ref, phase-6-finalize
  branch-cleanup standards
- Out of scope: finalize cost ordering (WS-01), argparse wording (WS-02), lessons
  pipeline and anchors (WS-04)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-review-currency | staged | Compare review SHAs, repair the issue-comment path, decide the await pair |
| PLAN-04-git-branch-mechanics | staged | Make branch-sync-state and prune-ref correct after cleanup deletes |

## Sequencing and Surface Notes

- PLAN-03 before PLAN-04 is preferred but not required; they touch different files
  (github/automatic-review vs git-workflow/branch-cleanup) and are file-disjoint.
- PLAN-03 must decide the coderabbit-required + review_rate_window_await pair together;
  demoting the bot back to optional without the await decision is the wrong remedy.
