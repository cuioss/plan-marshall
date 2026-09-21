envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules
epic=process-compliance
kind=finding
created=2026-09-19T13:05:36Z

# Move-back note: plan-dir return and forced worktree removal (finding 004 sequel)

## What was done

Post-merge teardown mirrored the move-in from `test-fidelity-rules-004`:

1. `mv` of `.plan/local/plans/test-fidelity-rules` from the worktree back to
   the main checkout (no sanctioned move-back verb outside
   `integrate_into_main`, which was unreachable from this ad-hoc flow).
2. `git worktree remove --force` on the worktree. The force flag was load-bearing
   and is disclosed, not normalized: the worktree carried exactly one dirty file,
   `uv.lock` (20/20-line churn, byte-identical in shape to the churn the build
   daemon leaves on the main checkout). It is regenerable lockfile churn from
   the project's own builds, not authored work; no authored change was
   discarded. The AGENTS.md stash/restore prohibition was honored by avoidance:
   nothing was stashed, nothing was restored, the churn was left in place on
   main untouched.
3. `prune-local-and-remote-ref` (sanctioned verb) for the local branch and the
   remote-tracking ref; the queue had auto-deleted the remote branch.
4. `switch-and-pull` refused on the dirty `uv.lock` (rebase guard); fell back to
   `fetch origin main` (read-only) and verified the squash merge `cd6436a4a` on
   `origin/main`. Local `main` left behind origin deliberately rather than
   forcing the pull through dirty state.

## Verified end state

- `git worktree list` holds no `test-fidelity-rules` entry; branch and
  remote-tracking ref gone; plan record resolves from the main checkout again.
