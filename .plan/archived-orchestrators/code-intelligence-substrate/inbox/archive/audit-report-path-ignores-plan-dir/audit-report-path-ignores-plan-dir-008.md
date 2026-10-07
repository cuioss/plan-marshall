envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T09:31:25Z

component=plan-marshall:plan-marshall
category=bug
title=The main_sha handshake invariant records the pinned cwd, so phase-5 stamps the feature branch

# main_sha records the pinned cwd, not main

## Observation

`handshakes.toon` for plan `audit-report-path-ignores-plan-dir` records, at the `5-execute` boundary:

```
main_sha    = 2475cd1794a8443d3ff01c85bf908898b4d3175f
worktree_sha= 2475cd1794a8443d3ff01c85bf908898b4d3175f
main_dirty  = 0
```

`git branch -a --contains 2475cd179` returns exactly one ref: `remotes/origin/feature/audit-report-path-ignores-plan-dir`. That commit **never reached main** — PR #1063 was squash-merged, so main received a different SHA entirely. The field named `main_sha` is holding a feature-branch-only commit, and it is identical to the `worktree_sha` column sitting directly beside it.

## Mechanism

Under ADR-002 the cwd is pinned to the plan's worktree from phase-5 onward. The handshake captures `main_sha` by reading HEAD of the current tree. Before phase-5 that happens to be main, so rows 1-4 are correct (`c259f5c` → `f8a3619` → `d38b769` → `d38b769`). From phase-5 it is the feature branch, and the field silently changes meaning.

The self-contradiction is structural, not incidental: a row where `main_sha == worktree_sha` while `worktree_sha` exists as a separate column is definitionally wrong unless the plan is running on main — and this plan's `use_worktree` is `true`.

## Downstream effect

`summarize-invariants` duly reported it as real drift:

```
warning, main_sha, main_sha drift 4-plan -> 5-execute: d38b769... -> 2475cd179...
```

Main did not move. Any consumer comparing `main_sha` across phases to detect "main advanced under us" gets a guaranteed false positive at the 4-plan→5-execute boundary of every worktree-backed plan. `main_dirty: 0` at that row is likewise a worktree reading, not a statement about main.

## Rule

- `main_sha` and `main_dirty` MUST be captured against the **main checkout explicitly** (`git -C {main_checkout}`), never against the pinned cwd. The main checkout path is resolvable independently of the worktree.
- Add an assertion at capture time: when `use_worktree` is true, `main_sha == worktree_sha` is a **capture bug**, not a valid state. Fail loud rather than persisting the row.
- Cross-phase `main_sha` drift warnings emitted at the 4-plan→5-execute boundary are currently untrustworthy for every worktree plan and should not be actioned until this is fixed.

## Relation to the corpus

Same polarity as the standing rule "never judge a merge lock stale from a worktree-scoped store — query the MAIN checkout; an empty worktree-scoped read is *unknown*". This is that rule violated at a different seam: not an empty read misinterpreted, but a worktree read *mislabelled* as a main read, with a correctly-named sibling column right next to it proving the mislabel.
