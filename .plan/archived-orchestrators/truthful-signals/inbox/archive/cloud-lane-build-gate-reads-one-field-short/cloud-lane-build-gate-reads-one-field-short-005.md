envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:15Z

component=plan-marshall:manage-change-ledger
category=bug
confidence=high
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=plan_efficiency,log_analysis

# Build-time oracle reported 0 builds while 52 build calls sit in the plan's own log

## Context

`analyze-logs` `build_time` block for this plan:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
```

Per the plan-efficiency contract, `build_count: 0` means "no ledger build rows — build time is
UNAVAILABLE (absent is not zero)". But the SAME fragment's `script_cost_rollup`, computed from the
plan's own `script-execution.log`, records:

```
"plan-marshall:build-pyproject:pyproject_build",52,9173400.0,0,57.022,680020.0
```

52 build invocations, 9,173,400 ms cumulative (about 2h33m), 57% of all script time in the plan.
Builds unambiguously ran. The change-ledger — the designated build-time ORACLE — carried no rows
for this plan.

## Root cause

NOT ESTABLISHED. Two observations bound it rather than explain it:

- `manage-change-ledger query --kind build` resolves `ledger_path` to
  `/Users/oliver/git/plan-marshall/.plan/work/change-ledger.jsonl` and returns 435 entries, the
  early ones carrying `plan_id: null`.
- Phases 5 and 6 ran with cwd pinned to the plan's worktree, which carries its own `.plan/` tree
  under the ADR-002 move model.

A worktree-anchored ledger that never merges back into the main-anchored one would produce exactly
this signature, but that is a hypothesis. It has not been verified and should not be recorded as
the cause.

## Proposed action

First establish where the 52 build rows went — check whether the worktree's `.plan/work/change-ledger.jsonl`
was written and whether `integrate_into_main` folds it back. Then either fold it at move-back or
anchor the ledger to main the way the merge lock is.

Until then, the reporting bug stands on its own and is worth fixing independently: `build_count: 0`
plus a non-empty `pyproject_build` rollup in the same fragment is an internally contradictory
report, and `analyze-logs` has both numbers in hand. It should say so rather than emitting a bare
unavailable.

## Evidence

- aspect: plan_efficiency — `build_time_provenance.contradiction`
- aspect: log_analysis — `build_time.build_count: 0` alongside
  `script_cost_rollup.ranked[0] = pyproject_build, 52 calls, 9173400 ms`
