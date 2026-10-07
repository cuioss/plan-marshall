envelope_version=1
sender_type=plan
sender_id=sweep-preambles-shipped-accessors
epic=test-quality
kind=candidate-lesson
created=2026-09-08T01:55:20Z

## Problem

`default:branch-cleanup` (order 70) removes the plan's worktree, but does not reconcile
the two `status.metadata` fields that describe it. After it runs, `status.json` still
carries:

- `metadata.use_worktree: true`
- `metadata.worktree_path: <the directory branch-cleanup just deleted>`

Every later phase-entry assertion then fails, because the Phase-Entry Worktree Assertion
requires that when `use_worktree == true`, `worktree_path` be non-empty AND resolvable on
disk. Post-cleanup neither condition can hold.

## Observed impact

Plan `sweep-preambles-shipped-accessors`, at the archive gate:

```text
phase_handshake findings-check --phase 6-finalize
  -> status: error, error: worktree_unresolved, reason: worktree_path_not_found
     "metadata.worktree_path='…/worktrees/sweep-preambles-shipped-accessors' does not
      exist on disk; phase entry refuses to advance."
```

Clearing `worktree_path` alone does not help — it fails the other arm:

```text
  -> status: error, error: worktree_unresolved, reason: worktree_path_missing
     "metadata.use_worktree==true but metadata.worktree_path is missing or empty"
```

The gate is satisfiable only by ALSO flipping `use_worktree` to `false`, which the
operator must do by hand with two `manage-status metadata --set` calls. Nothing in the
documented finalize flow instructs this, and the assertion's own documentation names this
exact scenario as its motivating case ("branch-cleanup removes the worktree, so a stale
`worktree_path` at entry would point at a directory cleanup is about to delete or has
already deleted on a re-entry") — it detects the state but nothing produces the repair.

Note the `--value` ergonomics compound it: `--value ""` and `--value ''` are both rejected
by argparse as "expected one argument"; only the `--value=` form clears a field.

## Directive

Make `default:branch-cleanup` reconcile the worktree metadata as part of removal, in the
same step that deletes the directory:

- set `metadata.worktree_path` to empty, and
- set `metadata.use_worktree` to `false`,

so the post-cleanup status honestly describes a plan that no longer has a worktree, and
every later phase-entry assertion passes without hand repair.

Consider whether `use_worktree` is carrying two meanings that should be separated: "this
plan was configured to run in a worktree" (historical, immutable) versus "a worktree
currently exists for this plan" (live, and what the assertion actually needs). Flipping the
former to `false` at cleanup makes the archived record understate what the plan did. If the
distinction matters to any consumer, add a `worktree_removed` marker rather than rewriting
the configuration flag.

Also accept `--value ""` in `manage-status metadata --set` so clearing a field does not
require knowing the `--value=` form.

## Why this matters

The assertion is correct and load-bearing — it exists to stop a phase resolving against a
deleted directory. The defect is that the step which creates the condition does not clear
it, so the guard fires on the system's own normal completion path rather than on a real
fault. A guard that every clean run must be hand-repaired past teaches operators to reach
for the override, which is exactly the habit it was built to prevent.
