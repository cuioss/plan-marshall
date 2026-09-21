envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=finding
created=2026-07-29T05:22:29Z

## `worktree-remove`'s 60s git timeout converts a slow removal into a permanently-force-only one

**Observed during the PLAN-92 / PR #1041 finalize run, at `branch-cleanup` → Remove Worktree.**

### What happened

First call:

```
status: error
error: worktree_remove_failed
message: "git worktree remove failed: git timed out after 60 seconds"
hint: Pass --force only after verifying the worktree is clean.
```

`git worktree remove` had already begun deleting the worktree's files when
the 60-second subprocess timeout killed it. A `git status --porcelain` on the
worktree then showed:

```
 D LICENSE.md
 D build.py
 D pw
 D pw.bat
```

Those four root-level files are not this plan's footprint (which was
`marketplace/bundles/**` + `test/**`). They are files the interrupted removal
had gotten to.

Second call, non-force retry:

```
fatal: '...' contains modified or untracked files, use --force to delete it
```

### The trap

The timeout **manufactures the exact dirty-tree condition that makes the
safe retry impossible.** After the first timeout there is no non-force path
back:

- non-force `worktree remove` refuses, because the tree is now "modified"
- the modification is not user work — it is the previous attempt's own
  partial deletion
- the standard's rule is explicit and correct in general: *"Worktree removal
  is non-force: Never pass `--force` to `git worktree remove`. Only clean
  worktrees may be removed. If the worktree has uncommitted changes, abort
  cleanup and surface the error — the user may still want to salvage the
  work."*

So the operator is asked to adjudicate a `--force` on a "dirty" tree whose
dirtiness is an artifact of the tool, with the hint text
(`"Pass --force only after verifying the worktree is clean"`) asking them to
verify a property that is now definitionally false.

### Theme fit

A **confident-signal-hides-a-caveat** instance on the error channel rather
than the success channel: `worktree_remove_failed` is one error code covering
two situations with opposite correct responses —

- *"the user has unsaved work here"* → never force, escalate, preserve
- *"I was interrupted midway through deleting this"* → forcing is the only
  correct completion, and is provably lossless

The second is reported in the vocabulary of the first. The `hint` field then
gives advice that is right for the first and misleading for the second.

### How it was resolved this run

Before prompting, the state was verified rather than assumed:

- `git status --porcelain` showed **only** the 4 deletions — no `??`
  untracked entries, so nothing unsaved existed
- none of the 4 paths was in this plan's footprint
- `git ls-tree --name-only HEAD -- LICENSE.md build.py pw pw.bat` on main
  returned all four — every file was recoverable from the merged HEAD
- `integrate_into_main` had already landed the plan dir back on main, so no
  plan state was in the worktree
- the branch was already merged

Only with all five confirmed was the operator asked, and they authorized
`--force`. Removal then succeeded immediately.

### Fix owed (tool layer, we own it)

1. **Distinguish the two failure modes in the returned error.** A timeout is
   not a dirty-tree refusal; it deserves its own code (e.g.
   `worktree_remove_timeout`) so the caller can branch. The current single
   code forces the caller to re-derive the distinction from a message string.
2. **On a timeout specifically, the retry guidance should be different.**
   Suggested shape: on `worktree_remove_timeout`, the standard's recovery
   should be *"re-inspect: if the only diff is deletions of tracked files
   that exist at the merged HEAD, and there are no untracked entries, the
   removal is resumable with `--force` and is lossless"* — i.e. codify the
   five-point verification above rather than leaving each operator to
   reinvent it under a hint that points the other way.
3. **Consider raising or making configurable the 60s git timeout for
   `worktree remove`.** This worktree carried a full marketplace tree plus
   `target/` output; 60s is tight for the file count on a busy filesystem,
   and the failure mode of being too tight is not "retry later", it is the
   one-way trap above.

### Related residue

The bare `git status --porcelain` inspection used to diagnose this had to be
run via `git -C`, because the plan-marshall content-search escape hatches are
all closed to a dispatched context (see msg 007). Diagnosing this class of
tool failure currently depends on the orchestrator context having tools the
leaves do not.
