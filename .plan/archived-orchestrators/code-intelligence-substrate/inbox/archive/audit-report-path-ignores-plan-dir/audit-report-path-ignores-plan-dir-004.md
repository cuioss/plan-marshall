envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T08:06:40Z

component=plan-marshall:phase-5-execute
category=improvement
title=At a phase-5 chain tail the Step 10a commit always invalidates the build stamp — post-commit verify is structural, not a flake

# Phase-5 tail: a stale pre-commit-verify-freshness verdict is structural

## Observation

At the tail of every phase-5 task chain in this plan, `pre-commit-verify-freshness` returned **stale**, and a post-commit verify was required before the chain could close.

This reads like a flake — a freshness check failing right after a green verify — and invites the wrong response (re-run and hope, or treat the stale verdict as noise).

## Mechanism

It is deterministic, and it follows from the ordering alone:

1. The chain runs verify; the build stamp records the tree at `worktree_sha = X`.
2. Step 10a commits. The commit **changes the worktree sha** to `Y`.
3. `pre-commit-verify-freshness` compares the stamp's `X` against the current `Y` and correctly reports **stale**.

The stamp was never wrong. The commit is what invalidated it, and the commit is unconditional at the chain tail. Therefore a post-commit verify at a phase-5 chain tail is a **structural requirement of the ordering**, not an anomaly.

## Rule

- Do **not** diagnose a stale `pre-commit-verify-freshness` at a phase-5 chain tail as a flake, a stamp bug, or a routed-build failure. Expect it.
- Do not attempt to "fix" it by re-stamping or by relaxing the freshness comparison — the freshness check is doing its job, and weakening it would reintroduce the false-green class it exists to catch.
- Budget the post-commit verify into the chain-tail cost model so the run does not read as over-budget or as retry churn.

## Open question for the epic

Whether the tail should be re-ordered (verify *after* the Step 10a commit, once) rather than verify-then-commit-then-verify-again. That would remove one full verify per chain tail. This is a design question about phase-5 step ordering, not a defect report — recording it so the epic can decide rather than each plan re-discovering the cost.
