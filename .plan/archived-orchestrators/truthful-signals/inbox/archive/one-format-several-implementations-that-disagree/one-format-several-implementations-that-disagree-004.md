envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T18:42:20Z

category=bug
component=plan-marshall:workflow-integration-git
title=worktree-remove and prune-local-and-remote-ref are not idempotent against each other

## Observed

In `branch-cleanup`'s post-merge cleanup, run in documented order:

1. `git-workflow worktree-remove --plan-id …` → `status: success`, `action: removed`,
   and its payload reports `branch: feature/one-format-…`. It had already deleted
   the local branch.
2. `git-workflow prune-local-and-remote-ref --plan-id …` →

```text
status: error
error_type: branch_delete_failed
local_deleted: false
message: "git branch -D feature/one-format-… failed: error: branch '…' not found"
```

The prune **aborted on that failure and never reached the remote-tracking ref**,
leaving `refs/remotes/origin/feature/one-format-…` in place — pointing at
`17843650c`, a branch already deleted on the remote by the merge queue. That is
precisely the stale ref the verb exists to remove.

Verified directly rather than inferred: `git ls-remote --heads origin <branch>`
returned empty (remote branch gone), while `git show-ref` still resolved the local
tracking ref. It was then deleted by hand — a single targeted `git branch -d -r`,
which the `branch-cleanup` constraints explicitly sanction as "provably scoped to
the current plan".

## The defect

`prune-local-and-remote-ref` documents an internal `show-ref` guard that "skips ref
deletion when already absent". That guard evidently covers the **remote-tracking
ref** but not the **local branch** — so an already-deleted local branch is a hard
error rather than a no-op, and because the verb fails fast, it takes the
still-needed remote-tracking prune down with it.

Two independent problems, either of which alone would be benign:

1. **Not idempotent.** A cleanup verb whose precondition its own sibling routinely
   destroys should treat "already gone" as success.
2. **Fails fast across independent sub-operations.** The local-branch delete and
   the remote-tracking prune have no dependency between them; sequencing them so
   the first can silently cancel the second turns a benign no-op into a leaked ref.

## How to apply

Give the local-branch delete the same already-absent guard the remote-tracking ref
has, and let the two sub-operations report independently rather than short-circuit.
Until then: after `branch-cleanup`, verify the remote-tracking ref is actually gone
rather than trusting the prune's return — and note the return was `status: error`,
so a caller that branches only on status would have surfaced a cleanup failure for
a tree that was, apart from the leaked ref, correctly cleaned.
