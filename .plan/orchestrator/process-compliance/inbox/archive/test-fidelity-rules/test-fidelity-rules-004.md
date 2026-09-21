envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules
epic=process-compliance
kind=finding
created=2026-09-19T10:47:42Z

# Move-to-worktree gap: sanctioned move-in cannot take a pre-existing branch

## Observed

Operator ordered the `test-fidelity-rules` checkin (branch
`feature/test-fidelity-rules`, commit `5194a64d0`, already pushed) off the main
checkout into a worktree. The sanctioned verb
`plan-marshall:workflow-integration-git:prepare_execute prepare` delegates to
`worktree-create`, which hardcodes `git worktree add -b {branch}` — branch
creation, not checkout. With the branch already existing (created inline during
the carve-1 shortcut), the sanctioned path fails instead of checking the
existing branch out.

## What was done instead (manual move, same end state)

1. `git checkout main` on the main checkout (freed the branch; unrelated dirty
   `uv.lock` rode along, untouched).
2. `git worktree add .plan/local/worktrees/test-fidelity-rules
   feature/test-fidelity-rules` (existing-branch checkout at `5194a64d0`).
3. `mkdir -p` the worktree `.plan/local/plans` parent, then `mv` of
   `.plan/local/plans/test-fidelity-rules` from main into the worktree —
   shell file operations, with no sanctioned plan-dir move verb available
   outside `prepare_execute`.
4. `generate_executor generate` from the worktree (worktree-bound executor).
5. Persisted `references.worktree_path` and
   `status.metadata.worktree_path`/`worktree_branch` (the Step 2.5 writes).

## Verified end state

- `locate-plan-checkout --plan-id test-fidelity-rules` returns
  `location: worktree` with the worktree path.
- Worktree: on `feature/test-fidelity-rules`, clean, tracking origin.
- Main: on `main`, only the pre-existing `uv.lock` modification remains.

## Request

- Teach `worktree-create`/`prepare_execute` the existing-branch case (check out
  when the branch exists, create with `-b` only when it does not), or document
  the manual move above as the sanctioned recovery.
- Until then, this filing records the `mkdir`/`mv` deviation and its
  justification rather than leaving it silent.
