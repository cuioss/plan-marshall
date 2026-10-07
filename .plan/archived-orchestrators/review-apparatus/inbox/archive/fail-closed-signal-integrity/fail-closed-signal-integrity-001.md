envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=review-apparatus
kind=finding
created=2026-08-02T21:28:51Z

# `ci pr merge` reported a merge that did not land, and deleted the branch anyway

## OBSERVED — first-party, 2026-08-02, plan `fail-closed-signal-integrity`, PR #1081

`ci pr merge --pr-number 1081 --strategy squash --delete-branch` returned:

```
status: success
operation: pr_merge
pr_number: 1081
strategy: squash
merged: true
branch_deleted: feature/fail-closed-signal-integrity
already_gone: false
```

The merge did not land. Verified three independent ways, after three separate
`git fetch origin` calls spread over several minutes:

1. `git merge-base --is-ancestor de00dca9b origin/main` → exit 1 (not an ancestor).
2. `git log origin/main --grep 1081` → no matching commit.
3. `origin/main` tip remained `5c41364a5` (#1079) throughout.

`ci pr list --head feature/fail-closed-signal-integrity --state all` reported the PR
`closed`; `ci pr view` reported `state: closed, mergeable: mergeable,
merge_state: clean`. No `gh-readonly-queue/*` branch existed for #1081 at any point
(`git ls-remote --heads origin 'gh-readonly-queue/*'` returned empty), so the work
was not sitting in a merge queue awaiting CI.

**The two halves of the operation diverged**: the branch deletion took effect on the
remote while the merge did not. That is the worst possible split — the reported
success is what a caller trusts, and the branch deletion removes the remote copy
that would otherwise make recovery obvious.

## Why this belongs to review-apparatus

The repo has `use_merge_queue: true`, and this is the merge/PR seam rather than a
measurement surface, so it routes here under the three-way rule rather than to
`truthful-signals` — even though the SHAPE is `truthful-signals`' flagship theme
(a confident affirmative derived from an outcome that did not occur).

## Why it matters beyond one PR

`branch-cleanup` treats the `pr merge` return as terminal. A caller that trusts
`merged: true` will:

- mark the merge step `done`,
- proceed to worktree removal and plan archival,
- and report the plan shipped.

In this run the operator caught it only because the orchestrator independently
re-derived `origin/main` after the call rather than trusting the return. Without
that check the plan would have archived itself as landed with its work present
nowhere on the remote — the branch having just been deleted by the same call.

This is precisely the standing rule *a landing claim is a lead* applied to the
merge verb itself: **`merged: true` is not evidence a merge landed.** The
corroborating check is `git merge-base --is-ancestor {head} origin/{base}` after a
fetch, and nothing weaker.

## HYPOTHESIS — not confirmed, do not action unverified

Under a required merge queue, `gh pr merge --squash --delete-branch` enqueues
rather than merges. If the provider layer maps the enqueue acknowledgement onto
`merged: true`, every queued merge would report as landed at enqueue time, and any
queue rejection afterwards would be invisible to the caller. That would make the
failure systematic under `use_merge_queue: true` rather than a one-off. **Neither
the provider mapping nor the queue's actual disposition of #1081 was read** — the
plan halted rather than investigating further, so this needs confirming at the
`github_ops` merge implementation before any fix is scoped.

## Recovery performed

Work was intact locally at `de00dca9b`. The branch was re-pushed and a replacement
PR opened (#1082) on operator decision. `#1081` was left closed rather than
revived. The merge mutex was released before halting, so no sibling plan was
blocked by the aborted merge.

## Suggested direction

Make the merge verb's success assertion corroborated rather than reported: after
the provider call, fetch and assert the head is an ancestor of the base before
returning `merged: true`, and distinguish `enqueued` from `merged` in the return
vocabulary so a queued merge is not indistinguishable from a landed one.
