envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=finding
created=2026-09-17T11:18:47Z

# Plan-dir duplication check — plan-03-review-currency move-in

Observation: operator reported the plan directory was duplicated instead of moved into the worktree.

Verdict: refuted — exactly one copy exists, in the worktree. The move-in worked as designed.

Evidence (all probed 2026-09-17, plan `plan-03-review-currency`):

- `git-workflow locate-plan-checkout` from main → `location: worktree`,
  `worktree_path: .plan/local/worktrees/plan-03-review-currency`.
- `manage-files list` from main → `error: dir_not_found` for
  `.plan/local/plans/plan-03-review-currency` (no main copy remains).
- `manage-files list` from the worktree → 12 entries: `artifacts/`,
  `build-results/`, `execution.toon`, `handshakes.toon`, `logs/`, `metrics.md`,
  `references.json`, `request.md`, `solution_outline.md`, `status.json`,
  `tasks/`, `work/`.
- `git worktree list` → exactly one worktree on
  `feature/plan-03-review-currency` (the sibling `git-branch-mechanics`
  worktree belongs to another plan; `/tmp/opencode/perm-red` is unrelated).
- `git status --porcelain` on main → clean (the phase-5 leaf wrote nothing
  to the main checkout).
- `prepare_execute` returned `action: moved`, consistent with every probe above.

Likely misread: the worktree-absolute plan path nests `.plan/local` twice
(`.plan/local/worktrees/{id}/.plan/local/plans/{id}`). That nesting is the
move-based model working as designed — each tree carries its own `.plan` —
not a copy.
