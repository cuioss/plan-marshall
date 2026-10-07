envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:48:01Z
lifecycle=superseded
superseded_by=dual-homed-hook-install-renders-identically-009.md

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=dual-homed-hook-install-renders-identically
source_aspects=plan_efficiency,logging_gap_analysis,log_analysis

# analyze-logs build_time reports an all-zero block when the ledger was unreachable

## Context

`analyze-logs` emitted this build_time block for a plan that ran 77 builds:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
  pass: 0
  error: 0
  timeout: 0
  killed: 0
  status_unknown: 0
```

The same fragment's `script_cost_rollup` ranks `plan-marshall:build-pyproject:pyproject_build` first at **77 calls / 16,475,540 ms — 67.3% of all script time in the plan**. Four of those builds hit a `timeout` or `failure` verdict during a two-hour incident window. None of it is in the build-time oracle.

`plan-efficiency.md` already tells the *reader* to render `build_count: 0` as `unavailable` rather than `0`. That rule is correct and this retrospective followed it. The defect is on the *producer* side: the block publishes no field saying whether the ledger was read, so a plan that genuinely ran no builds and a plan whose oracle was destroyed emit byte-identical output, and only external knowledge distinguishes them.

## Root cause

The change-ledger the oracle reads lives inside the plan's worktree — this plan's was at `.plan/local/worktrees/{plan_id}/.plan/work/change-ledger.jsonl`, named in a `[BLOCKED]` line at 23:24:25Z. `branch-cleanup` removes the worktree, and it runs at 08:00 while `plan-marshall:plan-retrospective` runs at order 995, at 09:04. The ledger is deleted before the only step that reads it. Nothing folds it into the plan directory at integrate-into-main the way the global logs are folded.

This is structural, not incidental: **every worktree-using plan reports `build_count: 0`** to its own retrospective, and every cross-plan roll-up that averages `total_build_seconds` averages in a zero for each of them.

## Proposed action

1. Fold `change-ledger.jsonl` into `{plan_dir}/logs/` (or `work/`) at integrate-into-main, alongside the global-log fold that already happens there.
2. Independently of (1), give the `build_time` block a ledger-availability discriminator — `ledger_state: present | missing | unresolved` plus the path consulted — so a zero always says which kind of zero it is. `build_count: 0` under `ledger_state: present` is a measured zero; under `missing` it is an unavailability.

## Evidence

- aspect: log_analysis — `build_time.build_count: 0` beside `script_cost_rollup.ranked[0] = pyproject_build, 77 calls, 16475540 ms, 67.282%`
- aspect: plan_efficiency — `build_time_provenance.rendered_as: unavailable`, `reason` naming the destroyed ledger
- work.log 2026-09-02T23:24:25Z `[BLOCKED]` line naming `ledger_path=/Users/oliver/git/plan-marshall/.plan/local/worktrees/dual-homed-hook-install-renders-identically/.plan/work/change-ledger.jsonl`
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].display_detail`: "merged via queue as 19453cb1b, worktree removed, refs pruned"
- `collect-plan-artifacts` manifest: 98 files in the plan directory, no `change-ledger.jsonl` among them
