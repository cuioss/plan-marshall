envelope_version=1
sender_type=plan
sender_id=git-branch-mechanics
epic=finalize-machinery
kind=finding
created=2026-09-17T11:18:30Z

# PLAN-04 worktree handling: copy/residue instead of clean move-in

Sender: plan `git-branch-mechanics` implementing
`.plan/orchestrator/finalize-machinery/plans/PLAN-04-git-branch-mechanics.md`.

## Observed state (all via manage-* scripts, no direct `.plan` reads)

- `git-workflow locate-plan-checkout --plan-id git-branch-mechanics` returns
  `location: worktree`,
  `worktree_path: /home/oliver/git/plan-marshall/.plan/local/worktrees/git-branch-mechanics`.
- `manage-files list --plan-id git-branch-mechanics` from the main checkout
  returns exactly one entry: `references.json`.
- The same `list` from the worktree path returns the full plan tree (12 entries:
  `request.md`, `status.json`, `references.json`, `solution_outline.md`,
  `tasks/`, `execution.toon`, `metrics.md`, `logs/`, `work/`, etc.).
- `manage-files read --plan-id git-branch-mechanics --file references.json`
  from main returns a stub containing only
  `worktree_path: .../worktrees/git-branch-mechanics`.
- The same read from the worktree returns the full record (`branch`,
  `base_branch`, `domains`, `scope_estimate`, `track`, `affected_files`,
  `worktree_path`).

So the plan state is split: a minimal `references.json` stub remains on main
while the authoritative copy lives in the worktree. Functionally this behaved
like a duplication/residue rather than a clean move-in.

## Timeline of my commands

1. Ran init through outline/plan inline and via `execution-context` dispatches,
   all on the main checkout (correct for phases 1-4).
2. At execute entry, `manage-status get-worktree-path` returned
   `worktree_state: pending`, `worktree_path: ""` (`not_yet_materialized: true`).
3. I did **not** run the orchestrator-side
   `workflow-integration-git:prepare_execute prepare --plan-id ... --branch
   feature/git-branch-mechanics` move-in from the main context, and I did not
   pin my own cwd to the worktree.
4. I dispatched `phase-5-execute` with `WORKTREE: .` and delegated the entire
   move-in to the leaf's Step 2.5, while I stayed on the main checkout.

## Why the residue likely happened

Primary hypothesis: the `worktree_path` stub on main was (re)created from the
main checkout after the move. Phase-5-execute Step 2.5 persists `worktree_path`
to both `references.json` and `status.metadata` after `prepare_execute`.
A write issued from a main-checkout cwd at that point recreates
`.plan/local/plans/git-branch-mechanics/references.json` containing only the
persisted field — exactly the stub observed. Contributing causes:

- I skipped the `execution.md` orchestrator cwd-pinning move-in and operated
  the execute dispatch from main.
- I forwarded `WORKTREE: .` (the main-checkout marker) even though the plan
  was `not_yet_materialized`, instead of materializing first and forwarding the
  resolved worktree path.
- After the leaf returned `status: blocked` (3 tasks done, orchestrator-tier
  `verify` yielded), I had not yet re-anchored; any further main-cwd
  plan-scoped write would deepen the split.

I cannot prove from the script outputs alone which exact call created the stub
(leaf Step 2.5 persist vs. a later main-cwd write); the shape matches a
post-move persist from the wrong cwd.

## Corrective action / what I will do differently

- At phase-5 entry, run `prepare_execute prepare` from the orchestrator,
  pin cwd to the returned `worktree_path` for the remainder of phase-5+,
  and only then dispatch the execute envelope with the resolved worktree.
- After the move, issue all plan-scoped reads/writes from the worktree-pinned
  context; treat any `.plan/local/plans/{plan_id}/` residue on main as suspect.
- Before finalize move-back, verify main holds no divergent plan stub and
  reconcile via the sanctioned move-back path rather than manual copying.

## Status of the plan itself

Plan `git-branch-mechanics` tasks report 3/3 complete in the leaf return;
orchestrator-tier `verify:quality-gate` / `verify:module-tests` were yielded
back to the orchestrator and are still pending. No finalize work has started.
