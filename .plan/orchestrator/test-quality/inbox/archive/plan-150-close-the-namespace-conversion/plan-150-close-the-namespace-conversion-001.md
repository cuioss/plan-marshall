envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:52:56Z

component=plan-marshall:manage-change-ledger
category=bug
confidence=high
source_plan=plan-150-close-the-namespace-conversion

# Attribute build-ledger rows to the running plan instead of NO_PLAN

## Context

The change-ledger at `.plan/work/change-ledger.jsonl` is the build-time ORACLE that
`plan-retrospective`'s plan-efficiency aspect reads for `total_build_seconds`. Across the
whole of 2026-09-02 the ledger recorded 27 build rows, and every single one carries
`plan_id: NO_PLAN`. Not one carries `plan-150-close-the-namespace-conversion`, even though
the plan's own `script-execution.log` records 175 `plan-marshall:build-pyproject:pyproject_build`
invocations totalling 9,489,980 ms — 71.5 percent of all script time the plan spent.

The retrospective therefore reported `build_count: 0` and rendered `total_build_seconds`
as `unavailable`. That is the correct rendering under the aspect's "absent is not zero"
rule, but it means no plan in this repository can currently be scored on build cost.

## Root cause

The ledger write site does not resolve the running plan's id when the build executes.
The plan ran in a worktree (`use_worktree: true`), and the surrounding evidence points at
the same worktree-vs-main resolution seam that produces `NO_PLAN`: an older row in the same
ledger records `worktree_resolution_failed` with `manage-status get-worktree-path returned
non-success: error='file_not_found' message='status.json not found'`. Whatever the precise
path, the outcome is that plan attribution is dropped at write time and cannot be recovered
afterwards.

## Proposed action

Resolve and stamp the running plan's id at the ledger write site rather than defaulting to
`NO_PLAN`, and make an unresolvable plan id an explicit recorded state rather than a
silent fallback that is indistinguishable from a genuine plan-less build. A build row whose
plan could not be determined should say so, so that a downstream `build_count: 0` can be
told apart from "this plan's builds were mis-filed".

## Evidence

- aspect: plan_efficiency — `build_time_provenance.build_count: 0`, `rendered_as: unavailable`
- aspect: log_analysis — `script_cost_rollup.ranked[0]`: `plan-marshall:build-pyproject:pyproject_build`, 175 calls, 9,489,980 ms, 71.479 percent share
- direct ledger query — `manage-change-ledger query --kind build` returns 99 rows, 27 of them dated 2026-09-02, all with `plan_id: NO_PLAN`, zero mentioning `plan-150-close-the-namespace-conversion`
