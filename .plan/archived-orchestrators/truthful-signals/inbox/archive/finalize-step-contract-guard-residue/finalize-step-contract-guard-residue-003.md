envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:22:45Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=finalize-step-contract-guard-residue

# Reconcile the build-time oracle with the script log before reporting four clean zeros

## Context

The `analyze-logs` aspect emits a `build_time` block sourced from the structured change-ledger:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
  pass: 0
  error: 0
  timeout: 0
  killed: 0
```

Four of those are health signals, and all four read clean. In the **same fragment**, produced by the **same script on the same plan**, `script_cost_rollup` reports:

```
"plan-marshall:build-pyproject:pyproject_build",112,28174490.0,0,88.649,1405600.0
```

112 build invocations, 28,174,490 ms (7h49m), 88.6 pct of all script time in the plan, slowest single call 1,405,600 ms. The plan directory holds 47 build-result logs, several over 5 MB.

So one block says no build ran and nothing timed out or was killed; the other measures 112 builds consuming the overwhelming majority of the plan's script time. A reader who takes `timeout: 0, killed: 0` as evidence of build health is reading a population the ledger never observed.

## Root cause

The `build_time` block is derived from the change-ledger (`summarize_build_ledger`), which recorded no rows for this plan. `build_count: 0` correctly means "no ledger rows", but the block renders the derived health counters as measured zeros rather than as unavailable. The aspect's own reference document already states the correct reading — "A plan with `build_count: 0` has **no ledger build rows** — its build time is UNAVAILABLE (absent is not zero)" — but the emitted TOON does not encode that distinction, so the discipline lives only in prose a downstream reader may not load.

## Proposed action

When `build_count == 0`, emit `total_build_seconds: unavailable` and either omit `pass` / `error` / `timeout` / `killed` or render them as `unavailable`, rather than as `0`. Additionally, cross-check the ledger against the script log inside `analyze-logs`: when the ledger reports zero builds while `script_cost_rollup` ranks a build wrapper in its top entries, emit a `ledger_coverage_gap` finding naming both counts. The two numbers are already computed in the same function — the reconciliation costs nothing.

## Evidence

- aspect: log_analysis — `build_time.build_count: 0` with `pass/error/timeout/killed` all `0`
- aspect: log_analysis — `script_cost_rollup.ranked[0]` = pyproject_build, 112 calls, 28,174,490 ms, 88.649 pct share
- artifact: 47 files under `build-results/`, several exceeding 5 MB
- reference: `plan-efficiency.md` — "absent is not zero", stated in prose but not encoded in the fragment
