envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:45:59Z

component=plan-marshall:manage-change-ledger
category=bug
confidence=high
source_plan=plan-truth-148
source_aspects=plan_efficiency,log_analysis

# Build-time oracle recorded 0 builds while the plan made 96 build-wrapper calls

## Context

`analyze-logs` reports `build_time.build_count: 0` for plan-truth-148, so the unified change-ledger
holds no `kind=build` row for this plan. The plan-efficiency aspect therefore renders
`total_build_seconds: unavailable` — correctly, since a `0` there would assert a measurement nobody
made and would average into every cross-plan roll-up as though the plan had built instantly.

The same plan's `script-execution.log` records 96 `plan-marshall:build-pyproject:pyproject_build`
calls totalling 41,041,370 ms — 73.97% of all script time the plan spent, and the single largest
entry in the cost rollup by a factor of seven.

## Root cause

Not diagnosed here. The observable is a two-surface disagreement: the executor log records the build
calls, and the ledger records none of them. Either the ledger write is not firing on this call path,
or it is firing and being written somewhere the plan-scoped read does not look.

## Proposed action

1. Establish which of the two surfaces is wrong before changing either. The executor log is the
   corroborating surface here, not the authority.
2. Treat this as freshness-gate-adjacent, not merely a reporting gap. `default:push` gates on the
   same ledger: it scans for a `kind=build` row matching the current `worktree_sha`, and an empty
   ledger is indistinguishable from the `worktree_mutated` stale route. A plan whose builds never
   reach the ledger passes that gate only by the exemption route, or not at all.
3. Publish the ledger row count alongside `build_count` so an empty ledger is legible as empty rather
   than as zero builds.

## Evidence

- aspect: plan_efficiency — `build_time_provenance.build_count: 0`, `rendered_as: unavailable`
- aspect: log_analysis — `script_cost_rollup.ranked[0]`:
  `plan-marshall:build-pyproject:pyproject_build`, 96 calls, 41,041,370 ms, 73.97% share
- aspect: log_analysis — `build_time.suspect_count: 0`, so this is not the suspect-zero floor case;
  there are no rows at all
