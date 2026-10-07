envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:45Z

component=plan-marshall:plan-marshall
category=bug
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Record orchestrator-tier verify builds against the plan

## Context

For this plan `module-tests plan-marshall` and `verify plan-marshall` exceed the Bash ceiling, so the execute leaf handed them back and the orchestrator ran them: four times in 5-execute, more in finalize. These are the only runs that executed the plan's tests. They left almost no trace in the plan:

- No `verify:module-tests` row in the execution log, although the manifest declares it in `phase_5.verification_steps`. The log holds `verify:compile` x3, `verify:quality-gate` x4 and `verify:test-compile` x2 - the steps the leaf ran itself.
- No result line in the work log. Each run shows only the build-busy title token being set and cleared.
- No log under the plan's `build-results/`. The leaf that needed the test log found it under the plan-less sentinel directory (`plans/NO_PLAN/build-results/plan-marshall/python-2026-10-01-101128.log`).
- The first run's failure (3 tests, caused by main) is recorded in the decision log only.

## Root cause

OBSERVED: the orchestrator-tier build path does not call `record-step` and does not attribute the build to the plan. HYPOTHESIS: the build was started without the plan id, which is why its results landed under the sentinel directory; the await-long-running workflow was not read to confirm.

Related and unexplained: the change-ledger was read (867 rows) and held no build row for this plan at all, so the retrospective reports build time as unavailable while the script log shows 23 build calls.

## Proposed action

1. In the orchestrator-tier verification path, start the build with the plan id so its results are filed under the plan.
2. After it returns, call `record-step` for the manifest step it satisfied and write one `[VERIFY]` line with the outcome and test count.
3. Establish why the plan's build rows are absent from the change-ledger the retrospective reads.

## Evidence

- dispatch-audit `firing_comparison` 5-execute: `execution_rows: 9`, none of them `verify:module-tests`
- manifest: `phase_5.verification_steps: [verify:quality-gate, verify:module-tests]`
- work.log title-token pairs at 2026-10-01T07:43:28Z-07:52:58Z, 09:52:07Z-10:00:01Z, 10:11:27Z-10:18:48Z, 10:29:41Z-10:38:22Z with no result line
- decision.log 2026-10-01T07:54:25Z (failure recorded only here), 10:24:01Z (job 590c79384ebb43ee8570924656c076a6)
- log-analysis `build_time`: `ledger_rows_scanned: 867`, `summed_rows: 0`, `log_build_calls: 23`
