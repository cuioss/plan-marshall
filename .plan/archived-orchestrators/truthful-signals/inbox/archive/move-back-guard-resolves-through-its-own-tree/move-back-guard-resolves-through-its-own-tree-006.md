envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:57:03Z

# A real-resolver fixture that places two resolvers at the SAME path cannot observe their divergence

**Component**: `plan-marshall:persona-module-tester` (standards/testing-methodology.md)
**Shape**: structural blindness in the FIXTURE, not in the guard or the loader.

## What the plan fixed

`cmd_worktree_remove`'s `plan_dir_not_moved_back` precondition probed the plan directory
through a **cwd-relative walk-up** instead of the main-anchored resolver, so a caller
standing inside the worktree satisfied the guard with the very plan-state copy the
removal was about to destroy.

## Why the existing test suite could not see it

Two independent blind spots, only the first of which the corpus already covers.

1. **Patched resolver.** A patched resolver returns whatever the test told it to and
   cannot report where the process is standing, so the pre-fix and post-fix
   implementations answer identically under it. This is already covered by
   `persona-module-tester` standards/testing-methodology.md
   S "Require a Real-Resolver End-to-End Test for Path-Resolver and Create Side Effects".

2. **Coincident geometry - NOT covered anywhere.** Even with every resolver real, a
   fixture that anchors `PLAN_BASE_DIR` at the same directory the main-anchored resolver
   probes makes the two resolvers return the *same* path. The discriminator is constant
   **by construction**. Such a suite fully satisfies the existing "use real resolvers,
   no stubs" rule and is still blind. That is what makes this a separate rule rather
   than a restatement: the covering rule's own success criterion is met by the
   defective fixture.

## Directive

When the defect under repair is *resolver A was used where resolver B was required*,
"use real resolvers" is not sufficient. The fixture must **place A and B at different
paths and vary only the axis on which they disagree**.

- **Name the axis explicitly.** Here it is *caller cwd*; the replacement suite
  `test/plan-marshall/workflow-integration-git/test_worktree_remove_cwd_geometry.py`
  varies cwd and nothing else, over a real `git init` main checkout with a real
  `git worktree add` linked worktree, via `monkeypatch.chdir`.
- **Mirror production geometry so the resolvers genuinely disagree.** The worktree is
  nested under main at `main/.plan/local/worktrees/{plan_id}`, so main is an ANCESTOR of
  the removal target and the containment test has to distinguish "inside the target"
  from "inside the repository". A flat sandbox would have made the two answers agree.
- **Walk the cross-product of the axes the preconditions read** (caller cwd x plan-dir
  residency), not the diagonal. Each cell differs from its neighbour along exactly one
  axis - that is what makes the pair matched, and it is what identifies which cells are
  the positive cases and which are the negative controls.
- **Demonstrate the positive cells failing against the pre-fix implementation.** That is
  the only evidence the suite can observe the defect at all. A suite that answers
  identically before and after the fix has proved nothing about the fix, regardless of
  how little it mocked.
- **Where a seam must still be stubbed, prove the stub is invariant along the varied
  axis.** Here `file_ops._query_worktree_path` is stubbed for a structural reason - the
  fixture anchors `PLAN_BASE_DIR` at the same store `_plan_dir_on_main_checkout` probes,
  so serving the persisted worktree path out of that store would fail for exactly the
  reason the guard is being asserted about and the run would never reach the guard. The
  stub returns one constant absolute path regardless of cwd, so it cannot mask a
  cwd-sensitive defect. State that invariance in the docstring; an unjustified stub in a
  geometry suite is indistinguishable from the blindness the suite exists to remove.

## Where it belongs

`plan-marshall:persona-module-tester` standards/testing-methodology.md, as a **second
review tell** in the real-resolver section alongside the existing one ("the module names
the path resolvers only in mock setup"):

> The fixture arranges the two resolvers to resolve to the same location. A suite can
> mock nothing at all and still be unable to observe which resolver the code used.

## Evidence

- `test/plan-marshall/workflow-integration-git/test_worktree_remove_cwd_geometry.py`,
  module docstring lines 3-72 (the axis, the geometry, the matrix, the positive/control
  split, and the single stub's cwd-invariance rationale).
- Plan `move-back-guard-resolves-through-its-own-tree`, PR #1361, merged `5f972ac15`.
