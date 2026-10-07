envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:30:03Z

# The build-time oracle reported build_count=0 while 315 build invocations ran

component: plan-marshall:plan-retrospective
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

`analyze-logs` `build_time` block:

```
total_build_seconds: 0.0
build_count:         0
suspect_count:       0
pass/error/timeout/killed/status_unknown: all 0
```

The SAME fragment's `script_cost_rollup` records, from the plan's own script log:

- `plan-marshall:build-pyproject:pyproject_build` — **191 calls**, 8,891,100 ms
  cumulative (29.1% of all in-plan script time), max 723,760 ms
- and in the folded global logs — **124 calls**, 10,628,400 ms (71.0% of that
  rollup), max 926,560 ms

315 build invocations, roughly 5.4 hours of wall time, and the change-ledger
oracle recorded not one row.

## Why the honest-rendering rule is not enough

`references/plan-efficiency.md` correctly requires the consumer to render
`total_build_seconds` as `unavailable`, never `0`, when `build_count == 0` —
"a `0` asserts a measurement nobody made". That rule fires and is right. But it
converts a **structural blindness** into a benign-looking absence: `unavailable`
reads as "this plan did not build", when the truth is "the ledger did not observe
315 builds that the script log records in the same file".

`build_count: 0` and `suspect_count: 0` together assert a clean, empty
population. There is no field distinguishing "no builds ran" from "the ledger was
not written".

## The generalizable rule

When two sources in the same artifact disagree about whether an event class
occurred, the reporting surface must say so rather than pick the emptier one. The
cheap fix here is a cross-check inside `analyze-logs` itself: it already computes
the build-script call count in `script_cost_rollup`, so a `build_count: 0`
alongside a non-zero `pyproject_build` call count is a detectable contradiction
that should be published as a finding, not resolved silently in favour of the
zero.
