envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:18:36Z

component=plan-marshall:manage-change-ledger
category=bug

# Build-time oracle recorded zero build rows against 59 real build calls

## Context

The plan-efficiency aspect is contractually required to render `totals.total_build_seconds` as `unavailable` rather than `0` whenever `log_analysis.build_time.build_count` is `0`, because an absent measurement must never be reported as an instant build. On this plan that rule fired — `build_count: 0`, `total_build_seconds: 0.0`, `suspect_count: 0`. Yet the same plan's own `script-execution.log` records 59 `pyproject_build` calls totalling 5,940,020 ms: roughly 99 minutes, 43.6% of all script time in the plan and by a wide margin its single largest cost. The build-time oracle did not observe the plan's most expensive activity.

## Root cause

The change-ledger is the declared build-time ORACLE, and `summarize_build_ledger` reads it exclusively — by design, so that build time spans every build system and every phase rather than only the pyproject calls a plan happened to log. But on this plan no ledger build rows were written at all, while the builds demonstrably ran and were logged elsewhere. Either the ledger write is not wired on the path these builds took (the build-server daemon long-poll mechanism — every one of the 59 calls resolved through `mechanism=daemon_longpoll`), or the rows were written somewhere the summarizer does not read.

## Proposed action

Establish whether the build-server daemon path writes change-ledger build rows at all. If it does not, wire the ledger write into that path so the oracle sees routed builds as well as direct ones. If it does, find why `summarize_build_ledger` read none. Until the gap is closed, every retrospective over a daemon-routed plan reports its build time as unavailable — which is the honest answer, but it means build cost is unmeasurable for the plans that use the fast path, i.e. increasingly all of them.

## Evidence

- aspect: plan_efficiency — `total_build_seconds: unavailable`, reason `log_analysis.build_time.build_count == 0`
- aspect: log_analysis — `build_time: {total_build_seconds: 0.0, build_count: 0, suspect_count: 0, pass: 0, error: 0, timeout: 0, killed: 0}`
- aspect: log_analysis — `script_cost_rollup.ranked[0]`: `plan-marshall:build-pyproject:pyproject_build`, 59 calls, 5,940,020 ms cumulative, 43.618% share, max 333,340 ms
- work.log — every build resolved via `[BUILD-SERVER] resolved build (requested=auto, resolved=routed, mechanism=daemon_longpoll)`
