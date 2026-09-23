# WS-05: Worktree-Isolated Ledger Landing

epic: orchestrator-refactor

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-worktree-isolated-landing.md` and is tracked in
> the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns aspect 5 of the epic (added 2026-09-23, operator-proposed): the orchestrator currently
persists `.plan/orchestrator/{slug}/` state by committing and pushing directly against
whatever checkout the session happens to be running in — today, almost always the primary
checkout on `main` — through ad hoc `git commit`/`git push` under the small-ops carve-out,
with no dedicated mechanism (confirmed: zero `git commit`/`git push` invocations anywhere in
`orchestrator.py` or its workflow docs). Across many concurrently-active epics this lands
frequent, unrelated commits directly on `main`'s history, which operator-observed
interferes with plan-marshall runs that inspect `main`'s state at various lifecycle phases.
This workstream confines all reads/writes of an epic's own orchestrator tree to a
FIXED-NAME, long-lived, per-epic git worktree (mirroring the existing
`.plan/local/worktrees/{plan_id}/` convention `workflow-integration-git` already
establishes for plans, but keyed by epic slug and never auto-removed), and replaces the ad
hoc commit/push with two explicit, monitored verbs — `land` (this epic's own pending
changes) and `land-all` (every active epic's pending changes, swept via `corpus epics`) —
that create/reuse a branch, open or update a PR, wait for CI via the existing bounded
`ci checks wait` primitive, merge, and pull the result into both `main` and the worktree
itself, all without deleting the worktree.

## Scope

- In scope: an `orchestrator.use_worktree` config knob (marshal.json, orchestrator block);
  fixed-name per-epic worktree creation/attach, idempotent and non-destructive; routing the
  orchestrator's store-resolution seam (`get_store_dir`/`get_tracked_config_dir`, the same
  resolver PLAN-01 introduced) through the worktree path when the knob is on; the `land` and
  `land-all` verbs themselves (branch, commit, push, PR, CI-wait, merge, pull-both,
  never-remove); failure/timeout handling that leaves a half-landed worktree intact for
  retry rather than silently discarding uncommitted or unpushed work.
- Out of scope: any change to how a PLAN's own worktree lifecycle works (that machinery,
  `git-workflow.py`'s `--plan-id`-addressed verbs, is reused/extended, not redesigned);
  the ledger DECOMPOSITION itself (WS-01/PLAN-02's concern — this workstream changes WHERE
  and HOW the tree is committed, not its internal file shape); review-bot participation on
  a landed PR (`.plan/**` is already excluded from CodeRabbit/PR-Agent review org-wide, and
  the whole-tree build's `skip-on-docs-only` footprint gate already fast-paths a
  non-buildable ledger-only diff — this workstream relies on both, changes neither).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-09-orchestrator-worktree-substrate | staged | The fixed-name worktree + config knob + resolver routing. Foundation PLAN-10 depends on. |
| PLAN-10-orchestrator-land-verbs | staged | `land` and `land-all` themselves — commit/push/PR/monitor/merge/pull-both, never-remove. Depends on PLAN-09. |

## Sequencing and Surface Notes

- PLAN-10 strictly depends on PLAN-09 (there is nothing to land until the worktree and its
  resolver routing exist).
- Both plans touch `tools-file-ops` (the shared resolver PLAN-01 already introduced) and
  potentially `workflow-integration-git`/`tools-integration-ci` — cross-bundle surface,
  same shape as WS-04's cross-bundle touch on `tools-epic-surface-partition`.
- Overlaps with every OTHER staged plan in this epic in one specific sense: once
  `orchestrator.use_worktree` is on, every other plan's own future ledger writes for THIS
  epic happen inside the worktree, not the primary checkout — a sequencing/rollout
  concern for whichever plan lands last before this workstream ships, not a file-surface
  collision the disjointness gate would catch (declared paths differ; the effect is
  behavioral, not textual).
