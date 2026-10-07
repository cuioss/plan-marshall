envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:54Z

# A plan read from inside one worktree cannot see a sibling plan in another

## Context

To test whether a queue-blocking sibling plan was alive, two reads were performed from inside this plan's worktree: `manage-status read --plan-id participation-credit-anchored-to-merge-candidate` returned `file_not_found`, and `manage-status list` did not carry the plan either. Both absences were read as evidence the plan was dead. It was alive and holding the merge mutex.

## Root cause

Under ADR-002 a phase-5+ plan's directory MOVES into its own worktree, so it is absent from the main checkout's plans directory by design. `manage-status read` takes no account of that and reports a plain `file_not_found`.

`manage-status list` is documented to merge worktree-resident plans (`location: worktree`) via `get_worktree_root()`, so its silence is the sharper question. The reads were issued from inside a sibling worktree, so the most likely mechanism is that the worktree scan resolved a worktree-local root rather than the main checkout's — but that mechanism is an inference from the observed behaviour, not something this run established. It should be derived before anything is changed.

The generalizable shape: two independent reads both returned absence, and both were structurally incapable of returning presence. Two blind checks agreeing is not corroboration.

## Proposed action

1. Make `manage-status read` fall back to `git-workflow locate-plan-checkout --plan-id {id}` on `file_not_found`, returning the plan's status from wherever it lives, or an explicit `lives_in_sibling_worktree` discriminator — never a bare absence.
2. Derive why `list` did not surface the plan when run from inside a sibling worktree, and fix the root resolution if that is the cause.
3. Treat `merge_lock check`'s own `staleness` field as the authority on holder liveness; never a `manage-status` absence read from a tree that cannot see the holder.

## Evidence

- Q-Gate finding `8d44fd` (severity error, still pending) records the full sequence and the corrected procedure
- ADR-002 — plan-scoped operations move into a cwd-pinned hermetic worktree
- `manage-status` SKILL.md documents the `list` worktree merge, which makes the observed silence a defect rather than expected behaviour
- The plan-marshall Auto-Detect path already runs `git-workflow locate-plan-checkout` before any status read — the correct pattern exists and was not reached here
