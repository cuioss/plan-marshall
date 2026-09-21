# PLAN-04: Make branch verbs correct after cleanup deletes

epic: finalize-machinery
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-git-branch-mechanics.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode +
Muse Spark 1.3): process compliance is mandatory, not advisory.

## Objective

Repair the two git branch-mechanics defects where individually correct steps are jointly
wrong: branch-sync-state cannot reach remote_absent_landed once branch-cleanup removed
the worktree (and the push default would re-push a merged-and-deleted branch), and
prune-local-and-remote-ref aborts on an already-deleted local branch, stranding the
remote ref. Ship verbs reachable in the states cleanup actually produces.

## Deliverables

1. branch-sync-state reaches remote_absent_landed after worktree removal (via recorded
   state or a non-worktree probe), with the push re-entry fail-toward-push default
   corrected for merged-and-deleted branches.
2. prune-local-and-remote-ref tolerates an already-deleted local branch and still
   prunes refs/remotes/origin/{branch}.
3. Branch-cleanup contract updated so the order worktree-remove → prune is either
   reordered or explicitly safe, with a regression test per defect.

## Claim Labels

- OBSERVED: branch-sync-state cannot reach remote_absent_landed once branch-cleanup removed the worktree, and the push re-entry default would re-push a merged-and-deleted branch — read at `.plan/orchestrator/finalize-machinery/epic.md` § `defect 3`
- OBSERVED: prune-local-and-remote-ref aborts on an already-deleted local branch, stranding refs/remotes/origin/{branch}, because worktree-remove deleted that ref first — read at `.plan/orchestrator/finalize-machinery/epic.md` § `defect 5`
- HYPOTHESIS: the two steps can be made jointly correct by tolerating the deleted-local state at the prune site and probing merge state without the worktree at the sync site — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` § `branch-sync-state` (verify-at-outline)
- Verify-first clause: the consuming phase confirms both mechanisms against git-workflow.py and the branch-cleanup standards at HEAD before scoping; refutation loops back to re-scope. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — branch-sync-state and prune verbs
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py` — prune-ref command
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — cleanup ordering contract
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` — cleanup re-review contract

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-01 shares the phase-6-finalize standards directory but different files (branch-cleanup vs ordering) — sequence behind PLAN-01 until it lands
- Adjacent to: PLAN-03 merge-gate work — no shared files, may parallelize once PLAN-01 lands

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-04-git-branch-mechanics.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
