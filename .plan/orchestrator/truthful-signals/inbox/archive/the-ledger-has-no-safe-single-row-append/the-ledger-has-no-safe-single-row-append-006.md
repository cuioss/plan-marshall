envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:20Z

component=plan-marshall:phase-5-execute
category=anti-pattern
confidence=high

# Check build freshness BEFORE reverting build-generated churn

## Context

Every build in this repository rewrites `uv.lock`. The pre-commit verify-freshness gate computes its currency hash over staged, unstaged AND untracked state, so any post-build edit to the worktree invalidates the freshness stamp that build just earned.

The trap is ordering. Reverting `uv.lock` AFTER the freshness check invalidates the stamp; re-running the build to recover the stamp rewrites `uv.lock` again and reproduces the loop. The plan hit this on 2026-09-06 and recorded it, then cited it again the next day as the reason a proposed remedy was declined.

The same churn had a second, separate cost. `uv.lock` maps to no registered module, so at 2026-09-05T20:51:19Z the pre-push quality gate could not scope itself and escalated to whole-tree. That whole-tree run timed out at 1070s under CPU contention and its retry took 30 minutes, costing roughly 76 minutes on a single step firing.

## Root cause

A build-generated file that belongs to no deliverable is treated as ordinary worktree state by both the freshness gate and the footprint scoper. The gate cannot tell "the agent changed source" from "the build touched its own lockfile", and the scoper cannot map the path to a module.

## Proposed action

Check freshness BEFORE reverting build-generated churn, and settle such a path in one direction before re-verifying rather than alternating. More durably: give the freshness gate and the footprint scoper a declared set of build-generated paths so a lockfile refresh neither invalidates a stamp nor forces a whole-tree escalation.

## Evidence

- decision.log 2026-09-06T09:06:28Z — "the freshness gate has an ORDERING TRAP - every build rewrites uv.lock, so reverting it AFTER the freshness check invalidates the just-earned stamp; check freshness BEFORE reverting."
- decision.log 2026-09-07T06:29:25Z — the trap cited as precedent while declining a generation-into-tracked-source remedy: "This plan already hit that exact ordering trap with uv.lock on 2026-09-06."
- work.log 2026-09-06T08:09:20Z — `[BLOCKED] ... build_scope_narrow ... refusing to transition 5-execute -> 6-finalize`; four verify submissions followed before the boundary cleared at 09:34Z.
- work.log 2026-09-05T20:51:19Z — "Footprint paths resolved to no registered module: uv.lock - proceeding whole-tree".
- decision.log 2026-09-05T20:17:14Z — operator disposition: revert in the worktree only.
