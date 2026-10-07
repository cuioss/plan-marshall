envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:36Z

component=plan-marshall:manage-architecture
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# A build whose resolved timeout budget is smaller than its own learned duration can only ever time out

## Observed

Three build-server waits in this plan returned `job_status=timeout` with an empty `elapsed` and an
empty `eta`, and produced **no verdict**:

```
[2026-08-29T15:16:50Z] build-server wait result: job_id=6e61bb355c9f4657911e85001fee80e6 job_status=timeout
[2026-08-29T16:21:53Z] build-server wait result: job_id=e53dcc1a50664d78919d2aa2cf11f9d4 job_status=timeout
[2026-08-29T16:40:06Z] build-server wait result: job_id=3b62b27889fe41aa8d280fc96fd246c9 job_status=timeout
```

The diagnosis reached during the run: **whole-tree `module-tests` resolves a `bash_timeout` of
657s against a learned duration of 1103s.** The budget is 60% of the observed duration, so the
configuration cannot succeed — not intermittently, not under load, but structurally. Two of the
three runs produced no verdict at all before the cause was identified.

## Why this is expensive

Build execution is the single largest cost line in the run:

| Population | calls | cumulative | share of script time |
|---|---|---|---|
| plan script-execution log | 56 | 2h33m | **41.3%** |
| folded-in global logs | 104 | 5h41m | **82.5%** |

A timed-out build is paid for in full — the work runs to completion server-side — and then
discarded. Three such runs is a substantial fraction of a plan's wall clock bought for nothing.

## The signal defect underneath the cost defect

`plan-retrospective`'s own `analyze-logs` aspect reports, for this plan:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  timeout: 0
  killed: 0
```

Zero builds, zero timeouts — in the same fragment whose `script_cost_rollup` ranks
`pyproject_build` first with **56 calls and 9,184,660 ms**. The `build_time` block is a confident
clean zero sitting beside its own contradiction, and `timeout: 0` is reported for a run in which
three builds timed out. Whatever population `build_time` samples, it is not the one a reader will
assume, and it publishes no denominator that would say so.

## Remedy (for the epic to scope)

1. **Make the budget derive from the learned duration**, with a margin, rather than being set
   independently of it. A resolved `bash_timeout_seconds` that is *below* the same resolver's
   learned duration for the same command is a detectable contradiction and should refuse or widen
   at resolve time, not fail at run time.
2. **Refuse rather than run.** A build launched under a budget it provably cannot meet should be
   rejected before it consumes the compute, with the two figures named in the refusal.
3. **Fix `analyze-logs`' `build_time` population.** Either it counts the builds the same log
   records — in which case `build_count: 0` is a bug — or it samples something narrower, in which
   case it must publish that population so a zero is legible. Currently it is a bare zero next to
   56 counted build calls.
