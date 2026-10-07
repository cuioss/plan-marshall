envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:41:26Z

component=plan-marshall:manage-change-ledger
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# The build-time oracle records no plan_id and stopped appending, so build time is permanently unavailable

## Context

`plan-efficiency` documents `totals.total_build_seconds` as **read verbatim** from the `log_analysis` fragment's `build_time.total_build_seconds`, which `analyze-logs.py` computes from the structured change-ledger via `summarize_build_ledger` — described in the reference as "the build-time ORACLE".

For this run the oracle returned:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
```

The same run logged, in its own `logs/script-execution.log`, **53** `plan-marshall:build-pyproject:pyproject_build` calls totalling **6,632,030 ms** (110.5 min, 44.8% of all script time), plus **36** more calls totalling **4,010,270 ms** in the folded-in global logs. Nearly three hours of build time, and the oracle counted none of it.

Direct inspection of the ledger explains why, twice over:

1. **It stopped appending.** `query --kind build` returns 436 rows; the newest is timestamped **2026-08-23T15:57:22Z**. This plan ran 2026-08-25T15:44Z → 2026-08-26T14:24Z. Zero rows were written during the entire ~23-hour run.
2. **No row is attributable to a plan.** Every sampled row (21 of 436 — the first 6 and the last 15) carries `plan_id` of either `null` or the literal `NO_PLAN`. And `query` exposes only `--kind` and `--exit-code`; there is no `--plan-id` filter at all. So even with rows present, a per-plan build total could not be computed from this surface.

The reference doc's own rule saves the report from lying — "Absent is not zero ... render `unavailable`, never `0`" — but the effect is that a documented, load-bearing cost measure is silently unavailable on every plan and nothing reports that.

## Root cause

Two independent faults that both point the same way: the ledger's producer stopped (or was never wired for the routed/daemon build path this run mostly used), and the ledger's schema never carried the attribution key its only consumer needs.

## Proposed action

1. Establish why appends stopped on 2026-08-23 — the run's builds went through both `daemon_longpoll` and `in_process_fallback` mechanisms, so check whether either path lost its ledger-append call.
2. Populate `plan_id` on every appended row and add `--plan-id` to `query`, so `summarize_build_ledger` can filter rather than returning the global set or nothing.
3. Have `analyze-logs` emit an explicit unavailability marker rather than `total_build_seconds: 0.0` alongside `build_count: 0`. A `0.0` in a numeric field reads as measured even when a sibling count says it was not; the render-side rule that catches this today lives in a different component from the field that carries the zero.

## Evidence

- aspect: `log_analysis` → `build_time.build_count: 0`, `total_build_seconds: 0.0`.
- aspect: `plan_efficiency` → `build_time_substrate` block: `ledger_build_rows_total: 436`, `ledger_last_build_row: 2026-08-23T15:57:22Z`, `ledger_build_rows_in_plan_window: 0`.
- `manage-change-ledger query --kind build` → `count: 436`, `ledger_path: /Users/oliver/git/plan-marshall/.plan/work/change-ledger.jsonl`.
- `manage-change-ledger query --help` → only `--kind` and `--exit-code`.
- aspect: `log_analysis` → `script_cost_rollup.ranked[0]`: `pyproject_build, 53 calls, 6632030 ms, 44.794%`.
