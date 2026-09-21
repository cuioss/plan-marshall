envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:17:08Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-07-29

# First phase-5-execute entry logs Re-entering instead of Starting when Step 2.5 short-circuits

## Context

On plan `self-review-cannot-see-an-unreachable-guard`, the `log-analysis` aspect's
`phase5_logging_gaps.dispatch_clustering` facts show `inferred_dispatches: 3`,
`starting_markers: 0`, `re_entering_markers: 3`. The rule expects exactly 1 "Starting execute
phase" line plus `clusters - 1 = 2` "Re-entering execute phase" lines for 3 dispatch clusters, but
0 Starting lines and 3 Re-entering lines were observed instead.

## Root cause

The very first phase-5-execute dispatch (`19:11:47`) logged `[STATUS] (plan-marshall:phase-5-execute)
Step 2.5 short-circuit: worktree_path already populated ... — skipping materialization`, followed
immediately by `19:12:44 [STATUS] (plan-marshall:phase-5-execute) Re-entering execute phase — 6
tasks pending` — i.e. the phase's normal "Starting execute phase" first-entry branch was bypassed
because the worktree was already materialized (self-absorbed zero-overlap drift absorbed 1 upstream
commit at `19:12:35` right before this), so the dispatcher took the re-entry logging path even
though this was genuinely the first phase-5 dispatch of the plan.

## Proposed action

In `plan-marshall:phase-5-execute`, decouple the Starting/Re-entering log-line choice from the
Step 2.5 worktree-materialization short-circuit — the two are orthogonal (worktree can be
pre-materialized on a genuinely-first phase-5 entry, e.g. after `phase-4-plan` pre-creates it).
Key the Starting/Re-entering choice on whether ANY task in `tasks_table` has been touched this
phase-5 lifetime, not on whether materialization ran.

## Evidence

- aspect: log-analysis — `phase5_logging_gaps.dispatch_clustering: {inferred_dispatches: 3,
  starting_markers: 0, re_entering_markers: 3}`
- work.log 19:11:47 (Step 2.5 short-circuit) immediately followed by 19:12:44 ("Re-entering execute
  phase — 6 tasks pending") with no prior "Starting execute phase" line anywhere in the session
