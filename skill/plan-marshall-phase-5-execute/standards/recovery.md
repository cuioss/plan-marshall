# Recovery Patterns

First-line responses for recovering an active plan worktree when external state shifts during phase-5-execute.

## Symptom: origin/main advances mid-plan, same files in disjoint regions

`origin/main` advances while the plan is mid-flight, and the new commit modifies the same files the plan is editing — but in different functions, sections, or blocks. A naive `git rebase origin/main` triggers conflict prompts even when there is no semantic conflict, and ad-hoc "fix the conflict" rounds regularly drop staged work or introduce regressions.

## Solution: stash + merge + pop

A repeatable three-move recovery handles the common case (same files, disjoint regions) cleanly without merge-conflict UI:

```bash
git -C {worktree_path} stash push -u -m "pre-merge-recovery"
```

```bash
git -C {worktree_path} merge origin/main
```

```bash
git -C {worktree_path} stash pop
```

`stash push` captures the plan's working-tree edits (including new untracked files via `-u`); `merge origin/main` brings the unmodified regions of the touched files up to date; `stash pop` re-applies the plan's edits on top. When the regions are disjoint, git's three-way merge of the stashed working tree resolves automatically with no conflict markers.

Each command is a separate Bash invocation — the one-command-per-call hard rule prohibits chaining with `&&`, `;`, or newlines.

## When this works

- Both sides modify the SAME files but in DISJOINT regions (different functions, different sections, different blocks).
- The plan's edits are still in the working tree (uncommitted) — they are exactly what `stash push` captures and what `stash pop` re-applies.
- `-u` is essential when the plan has produced new untracked files (new task files, generated artefacts, new test fixtures) that must survive the merge.

## When this does NOT work

- Both sides edit the SAME region of the SAME file. `stash pop` will surface a real conflict that needs human resolution. Use the same merge-conflict tooling you would use for any in-region collision; the stash-and-pop pattern provides no shortcut.
- The plan's edits are already committed on the working branch. Use `git -C {worktree_path} merge origin/main` (or `git -C {worktree_path} rebase origin/main`) directly — the stash dance is unnecessary and `stash pop` would be a no-op.
- The merge has destructive intent (e.g. you want origin/main to overwrite the plan's edits). Stash + merge + pop preserves the plan's edits; pick a different recovery if that is wrong.

## Why prefer this over rebase

`git rebase origin/main` rewrites every plan commit, which on a long-running plan means re-resolving the same disjoint-region case once per commit. The stash-and-pop sequence applies the resolution exactly once, against the working tree, and leaves history unchanged. For phase-5-execute mid-run recoveries this is the lower-risk path; rebases remain appropriate for pre-PR cleanup of commit history during phase-6-finalize.

## When to fall back

Keep these as explicit fallbacks when the disjoint-region precondition above does not hold:

- `git -C {worktree_path} rebase origin/main` — appropriate for pre-PR history cleanup, or when the plan has already committed its edits.
- Manual conflict resolution with the project's preferred merge tooling — the only correct path when both sides edit the same region of the same file.
