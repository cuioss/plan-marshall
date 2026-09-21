envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=candidate-lesson
created=2026-09-06T19:30:21Z

# The change-ledger has accepted no row since 2026-09-04 and the freshness gate reads it

component: plan-marshall:manage-change-ledger
category: bug
confidence: high
source_plan: exit-code-convention-stops-at-the-skill-boundary
source_pr: 1423, 1429

## Context

The unified change-ledger (`.plan/work/change-ledger.jsonl`) has received **no row
of either kind** since **2026-09-04**:

- `query --kind build` → `count: 444`, latest `timestamp_iso 2026-09-04T09:55:39Z`
- `query --kind job` → `count: 40`, latest `timestamp_iso 2026-09-04T09:54:45Z`

This plan ran **8 daemon-routed `pyproject_build` jobs** between
`2026-09-05T12:55:57Z` and `2026-09-06T16:49:32Z` (job ids `57a3f0e9…`,
`37b53b9d…`, `63d3e089…`, `67faf8de…`, `02e85889…`, `69c9b69d…`, `ab68c968…`,
`d52dddf1…`), **two of which failed**. It contributed zero rows.

The claim is derived, not sampled: the ledger is append-only and time-ordered, so
its maximum timestamp bounds everything after it.

A secondary decay is visible in the `kind=job` rows, which are small enough to
enumerate in full (all 40 returned): the last row carrying a **real plan id** is
`2026-07-30` (`plan-less-pr-can-be-opened-but-never-corrected`). Every row from
`2026-08-07` onward carries `NO_PLAN`. So plan-attributed rows stopped about a
month before the ledger stopped entirely.

## Root cause

Not yet established, and deliberately not asserted. Two candidate mechanisms were
considered and one was **refuted**:

- **Refuted — worktree-scoped store.** The ledger resolves via
  `file_ops.get_tracked_config_dir`, and rows carrying real plan ids (which run in
  worktrees) *did* land historically, so the store is reachable from a plan
  context and is not being lost with the worktree.
- **Open.** Something in the executor's dispatch-boundary `kind=build` writer, or
  in the daemon-routed (`mechanism=daemon_longpoll`) path, stopped appending on or
  about 2026-09-04. The stop predates this plan (which began 2026-09-05T08:07), so
  this plan did not cause it.

## Proposed action

1. Establish why appends stopped on 2026-09-04 — bisect the executor
   dispatch-boundary writer and the `daemon_longpoll` result path against that
   date.
2. Add a liveness assertion: a build that completes and writes no ledger row is a
   defect the build wrapper should surface, not a silent no-op.
3. **Check the blast radius before the retrospective one.** `_ledger_core`'s own
   docstring names two readers — the `query` verb *and* the
   `pre-commit-verify-freshness` gate. A freshness gate judging build currency
   from a ledger that has received nothing for days is the higher-severity
   exposure; the retrospective's `build_time` block is only the symptom that made
   it visible.

## Evidence

- `manage-change-ledger query --kind build` — 444 rows, max ts `2026-09-04T09:55:39Z`
- `manage-change-ledger query --kind job` — 40 rows (full enumeration), max ts `2026-09-04T09:54:45Z`
- `work.log` — 8 `build-server submit queued` / `build-server wait result` cycles on 09-05 and 09-06,
  with `job_status=failure` at `2026-09-05T17:01:59Z` and `2026-09-06T07:46:17Z`
- `fragment-log-analysis` — `script_cost_rollup` ranks `pyproject_build` first at
  11,246,620 ms (60.8% share, 18 calls), against `build_time.build_count: 0`
- `_ledger_core.py` module docstring — names `pre-commit-verify-freshness` as the second reader
