envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:18Z

component=plan-marshall:build-pyproject
category=improvement
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Record a change-ledger row per build so build time stops reading as unavailable

## Context

This plan ran 155 `pyproject_build` calls consuming 16,262,880 ms — 71.1% of all in-plan script time, and by a wide margin the single largest cost in the run. The plan-efficiency aspect nevertheless reports `total_build_seconds: unavailable`, because `analyze-logs` derives build time from the structured change-ledger (`summarize_build_ledger`) and that ledger recorded `build_count: 0` for this plan.

## Root cause

The build wrapper does not append a change-ledger row per invocation. The ledger is the declared build-time ORACLE, so with no rows it correctly reports "no measurement" rather than a fabricated zero — the contract behaves exactly as specified. The defect is upstream: the measurement is never written, so the honest answer is the useless one.

## Proposed action

Have the build wrapper append one change-ledger row per invocation at the point it already knows all three fields — `command`, `duration_seconds`, and the pass/error/timeout/killed verdict. The suspect-zero and `killed`-is-separate-from-`error` rules the aspect already applies then have real rows to apply to, and cross-plan roll-ups stop treating heavy-build plans as unmeasured.

## Evidence

- aspect: log_analysis — build_time.build_count 0, total_build_seconds 0.0, suspect_count 0 (nothing to be suspect about: there were no rows)
- aspect: log_analysis — script_cost_rollup.ranked: `plan-marshall:build-pyproject:pyproject_build` 155 calls, 16,262,880 ms, share_pct 71.052, max_ms 478,810
- aspect: plan_efficiency — totals.total_build_seconds rendered `unavailable`, never 0, per the absent-is-not-zero rule
