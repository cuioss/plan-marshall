envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T15:02:44Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-08-02
bundle=plan-marshall

# Order plan-retrospective so it reads a settled plan, not one mid-teardown

`plan-marshall:plan-retrospective` sits at manifest position **17 of 22** — AFTER
`branch-cleanup` (16) and BEFORE `record-metrics` (20). Both neighbours break it, in opposite
directions.

## Context

**Too late for the footprint.** `branch-cleanup` had already removed the worktree and merged the
branch, so `check-artifact-consistency` derived an **empty** footprint and reported
`affected_files_recall: fail — Recall 0% below 70% threshold`, listing all 8 declared files as
missing. The true footprint is exactly those 8 files — verified against the squash-merge commit
`5c41364`, which carries 8 files, 396 insertions, 55 deletions. **100% recall, exact set match in
both directions.** The aspect reported total coverage failure on a plan with perfect coverage.

The obvious workaround is worse. Passing the plan's phase-4 base SHA to
`check-manifest-consistency` produced `files_total: 39, files_kept: 37`, because three sibling PRs
(#1076, #1077, #1078) landed between that base and HEAD. Only 8 of the 39 belong to this plan — a
4.6x over-count. **A `base..HEAD` range is not a usable fallback: sibling landings contaminate it.**

**Too early for the metrics.** `record-metrics` has not run yet, so `metrics.md` still carries
`6-finalize` with a `start_time` and no `end_time`. Finalize is the **single largest phase of this
plan** — 1,767,890 tokens across 12 dispatched steps, more than phases 1-5 combined (1,505,604) —
and the retrospective reads it as zero. The reported Total understates actual spend by 2.17x.

The partiality machinery worked exactly as designed: `metrics.md` correctly carries
`> Partial: unrecorded phases — 6-finalize` and the Total is stamped `n=4/6`. The floor-not-truth
contract is honest. The problem is that the retrospective is scheduled at the one moment when that
floor is furthest from the truth.

## Root cause

The retrospective's inputs are anchored on two things the surrounding finalize steps destroy or
have not yet produced: the **worktree/branch pair** that identifies the plan's footprint, and the
**closed metrics row**. Its manifest position sits between the step that removes the first and the
step that writes the second, so **there is no ordering at which both are available** unless the
footprint is re-anchored on a durable artifact.

## Proposed action

Two independent fixes; neither subsumes the other.

**(a) Re-anchor footprint derivation on a durable artifact.** Add a resolver that falls back, in
order: (1) the live worktree diff, (2) the plan's own merge commit (recorded at `branch-cleanup`),
(3) `references.affected_files`. It must **never silently return an empty set** — an unresolvable
footprint is an error state, not a 0% recall verdict. Explicitly exclude `base..HEAD` from the
fallback chain.

**(b) Move `record-metrics` ahead of `plan-retrospective`** in the finalize `order:` frontmatter,
or have `plan-retrospective` fold the `6-finalize` accumulator itself before reading `metrics.md`.

## Why this matters beyond one bad number

A 0% recall verdict is the loudest signal this aspect can emit, and it fired on the plan's
*best-behaved* dimension. A reader who trusts the report concludes the plan missed its entire
declared scope. This is the confident-signal-hides-a-caveat shape pointed at the retrospective
itself — the instrument that is supposed to catch that shape in other components.

## Recurrence note

This is the **finalize-ordering archetype** again. The prior instance (PLAN-10, #1036) was "a plan
that fixes a finalize-time component cannot have that fix exercised by its own finalize." This is a
sibling, not a duplicate: **a retrospective ordered between teardown and metrics-close cannot
measure the plan it audits.** Same root shape — a finalize step whose position denies it the state
it needs.

## Evidence

- aspect `artifact_consistency` — `affected_files_recall,fail,Recall 0% below 70% threshold`; `declared: 8, found: 0`, all 8 under `missing[8]`
- `git show --stat 5c41364` — exactly the 8 declared files; zero drift in either direction
- aspect `manifest_decisions` — `base: b5477589…`, `files_total: 39`, `files_kept: 37` against a true footprint of 8
- aspect `plan_efficiency` — `metrics.md` Total 1,505,604 (n=4/6) vs derived 3,273,494; `understatement_factor: 2.17`
- `execution.toon` `phase_6.steps` — `branch-cleanup` (16), `plan-marshall:plan-retrospective` (17), `record-metrics` (20)
- `metrics.md` line 7 — `> Partial: unrecorded phases — 6-finalize`
